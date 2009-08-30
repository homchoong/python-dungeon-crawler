from pygame import *
import pygame
import random
import os
from pdcglobal import *
from key_mapping import *
from shadowcast import *

class Engine(object):
    def __init__(self):
        self.message_queue = []
        self.actors = []
        self.items = []
        self.quit_loop = False
        self.quit_mes = QUIT
        self.time = 0    
            
        Debug.init_debug(self)
        Debug.debug('creating game')
        
        Debug.debug('init pygame')
        pygame.init()
        Debug.debug('setting screen')
        self.screen = pygame.display.set_mode((800, 600))
        self.load_font()
        
        from dungeon.map import Map, testmap
        from item import *
        from actor import Actor, Player
        from npc import *
        
        Map.game = self
        Actor.game = self
        Item.game = self
        AI.game = self
                
        self.map = Map(testmap)
        self.sc = sc(self.map.map_array)
        #self.map = Map.Random()
        self.player = Player()
        self.player.cloak = Cloak()
        self.player.left = Flail()
        self.player.x, self.player.y = self.map.get_random_pos()
        Slug()
        #self.actors.append(self.player)
        #self.actors.append(Slug())
        #self.actors.append(FloatingEye())
        
        self.xoff = 0
        self.yoff = 0 
        self.buffer = False
    
    def re_init(self):
        Debug.debug('re_init')
        self.quit_loop = False
        self.quit_mes = QUIT
        if hasattr(self, 'map'):
            self.map.cur_surf = None
                
        from dungeon.map import Map
        from actor import Actor, Player
        
        Map.game = self
        Actor.game = self
    def load_font(self):
        self.std_font = pygame.font.Font(os.path.join('font', 'jesaya.ttf'), 14)    
    def start(self):
        Debug.debug('starting mainloop')
        return self._main_loop()
    def is_move_valid(self, actor, old_pos, new_pos, move_mode):
        for act in self.actors:
            if act.x == new_pos[0] and act.y == new_pos[1] and actor != act:
                return act
            
        return self.map.is_move_valid(old_pos, new_pos, move_mode)
    def attack(self, attacker, victim):
        defence = victim.get_total_dv()
        attack = attacker.get_total_av()
        attack += d(100) + d(50)
        defence += 100 + d(100)
        Debug.debug('%s Attack: %i' % (attacker.name, attack))
        Debug.debug('%s Defense: %i' % (victim.name, defence))
        
        if victim == self.player:
            vi_adress = 'you'
        else:
            vi_adress = 'the ' + victim.name
        
        if attack >= defence:
            damage = random.randint(attacker.get_total_min_damage(), attacker.get_total_max_damage())
            Debug.debug('Hit for %i damage!' % (damage))
            killed = self.do_damage(victim, damage)
            if attacker == self.player:
                at_adress = 'You hit'
            else:
                at_adress = 'The ' + attacker.name + ' hits'
            self.message_queue.insert(0, '%s %s for %i damage.' % (at_adress, vi_adress, damage))
            if killed:
                if attacker == self.player:
                    at_adress = 'You killed'
                else:
                    at_adress = 'The ' + attacker.name + ' killed'
                self.message_queue.insert(0, '%s %s' % (at_adress, vi_adress))
        else:
            if attacker == self.player:
                at_adress = 'You miss'
            else:
                at_adress = attacker.name + ' misses'
            
            self.message_queue.insert(0, '%s %s.' % (at_adress, vi_adress))
            Debug.debug('Miss!')
            
        attacker.cur_endurance -= 2
        victim.cur_endurance -= 2
        
    def do_damage(self, act, dam):
        act.cur_health -= dam
        if act.cur_health < 1:
            act.die()
            Debug.debug('%s dies of damage' % (act.name))
            return True
        return False
    
    def _save_quit(self):
        for act in self.actors: act.cur_surf = None
        for item in self.items: item.eq_img_c = None;item.dd_img_c = None
        self.quit_loop = True
        self.quit_mes = SAVE
    def _main_loop(self):
        while not self.quit_loop:
            self._world_move()
            self._world_draw()
            self._world_input()
            
        self.std_font = None
        return self.quit_mes
    def _world_input(self):
        for e in pygame.event.get():
            self.quit_loop = e.type == pygame.QUIT 
            
            if e.type == pygame.KEYDOWN:
                self.__handle_keydown(e.key)
    def _world_move(self):
        
        #actors with lowest timer first
        self.actors.sort(self.__sort_by_time)
        
        #for act in self.actors:
            #print act.name,act.timer
        
        #wait for player input
        if self.player.timer <= 0: return
        
        diff = self.actors[0].timer
        self.time += diff
        
        #Debug.debug('Worldtime: %s' % (self.time))
        
        #act-independent issues
        if self.time > 500:
            [act.tick() for act in self.actors]
            self.time -= 500
                
        for actor in self.actors:
            if actor.timer > 0:
                actor.timer -= diff
            else:
                actor.act()
    def _world_draw(self):
        self.screen.fill((0, 0, 0))
        self.screen.blit(self.__get_map_surface(), (0 + self.xoff, 0 + self.yoff))
        [self.screen.blit(self.__get_actor_surface(act), (act.x * TILESIZE + self.xoff, act.y * TILESIZE + self.yoff)) for act in self.actors if self.sc.lit(act.x, act.y) or act == self.player]
        self.screen.blit(self.__get_message_surface(), (0, 600 - 128))
        self.screen.blit(self.__get_statblock_surface(), (800 - 192, 0))
        pygame.display.flip()

    def __get_map_surface(self):
        if self.map.cur_surf == None:
            surf_map = pygame.Surface((self.map.width * TILESIZE, self.map.height * TILESIZE))
            self.sc.do_fov(self.player.x, self.player.y, self.player.mind / 20 + 2)
            for x in xrange(self.map.width):
                for y in xrange(self.map.height):
                    if (x == self.player.x and y == self.player.y) or self.map.map_array[y][x][MT_FLAGS] & F_MEMO or self.sc.lit(x, y):
                        blit_position = (x * TILESIZE, y * TILESIZE)
                        surf_map.blit(self.map.get_tile_at(x, y), blit_position)
                        if not self.map.map_array[y][x][MT_FLAGS] & F_MEMO:
                            tile = self.map.map_array[y][x]
                            new_tile = tile[0], tile[1], tile[2] ^ F_MEMO
                            self.map.map_array[y][x] = new_tile
                            
            self.map.cur_surf = surf_map
        
        return self.map.cur_surf
    def __get_actor_surface(self, act):
        if act.cur_surf == None:
            surf_act = pygame.Surface((TILESIZE, TILESIZE), pygame.SRCALPHA, 32)
            surf_act.blit(act.get_tile(), (0, 0)) 
            act.cur_surf = surf_act
        return act.cur_surf
    def __get_message_surface(self):
        surf = pygame.Surface((800 - 192, 128))
        surf.fill((120, 120, 0))
        y = 100
        for mes in self.message_queue:
            text = self.std_font.render(mes, True, WHITE)
            surf.blit(text, (0, y))
            y -= 20
        return surf
    def __get_statblock_surface(self):
        surf = pygame.Surface((192, 600))
        surf.blit(load_image('stat.png'), (0, 0))
        
        head = load_image('48.png')
        surf.blit(head, (192 / 2 - 24, 16))
        
        hand = load_image('48.png')
        lefth = pygame.transform.smoothscale(self.player.left.get_dd_img(), (48, 48))
        hand.blit(lefth, (0, 0))
        surf.blit(hand, (192 / 2 - 80, 72))
        
        hand = load_image('48.png')
        righth = pygame.transform.smoothscale(self.player.right.get_dd_img(), (48, 48))
        hand.blit(righth, (0, 0))
        surf.blit(hand, (192 / 2 + 32 , 72))
        
        front = load_image('48.png')
        surf.blit(front, (192 / 2 - 24, 72))
        surf.blit(front, (192 / 2 - 24, 126))
        
        feet = load_image('48.png')
        surf.blit(feet, (192 / 2 - 24, 184))
        
        ps_body = pygame.transform.smoothscale(self.player.cloak.get_dd_img(), (48, 48))
        surf.blit(ps_body, (192 / 2 - 24, 72))
        
        stats = [
            self.std_font.render('Strength: ', True, WHITE),
            self.std_font.render('Endurance: ', True, WHITE),
            self.std_font.render('Mind: ', True, WHITE),
            self.std_font.render('Speed: ', True, WHITE),
            self.std_font.render('Health: ', True, WHITE)]
            
        y = 235;
        for line in stats:
            surf.blit(line, (16, y));y += 18
        
        stats = [
               self.std_font.render(str(self.player.strength), True, WHITE),
            self.std_font.render(str(self.player.endurance), True, WHITE),
            self.std_font.render(str(self.player.mind), True, WHITE),
            self.std_font.render(str(self.player.speed), True, WHITE),
            self.std_font.render(str(self.player.health), True, WHITE)]
        y = 235;
        for line in stats:
            surf.blit(line, (90, y));y += 18                

        stats = [
               self.std_font.render(str(self.player.cur_strength), True, GREEN),
            self.std_font.render(str(self.player.cur_endurance), True, GREEN),
            self.std_font.render(str(self.player.cur_mind), True, GREEN),
            self.std_font.render(str(self.player.cur_speed), True, GREEN),
            self.std_font.render(str(self.player.cur_health), True, GREEN)]
        y = 235;
        for line in stats:
            surf.blit(line, (120, y));y += 18                

        stats = [
               self.std_font.render('Attack: ', True, WHITE),
               self.std_font.render('Defense: ', True, WHITE),
               self.std_font.render('Damage: ', True, WHITE)
               ]
        
        y = 330;
        for line in stats:
            surf.blit(line, (16, y));y += 20
                
        stats = [
               self.std_font.render(str(self.player.get_total_av()), True, WHITE),
               self.std_font.render(str(self.player.get_total_dv()), True, WHITE),
               self.std_font.render(str(self.player.get_total_min_damage()) + '-' + str(self.player.get_total_max_damage()), True, WHITE)
               ]                
        y = 330;
        for line in stats:
            surf.blit(line, (90, y));y += 20    
            
        return surf
    def __sort_by_time(self, a, b):
        return a.timer - b.timer
    def __handle_keydown(self, key):
        if key == pygame.K_F8:
            self._save_quit()
        
        if key in MOVES:
            self.player.move(key)
        
        if key == pygame.K_DOWN:
            self.yoff -= TILESIZE
        if key == pygame.K_UP:
            self.yoff += TILESIZE
        if key == pygame.K_LEFT:
            self.xoff += TILESIZE
        if key == pygame.K_RIGHT:
            self.xoff -= TILESIZE
        
        #test
        if key == MOVE_WAIT:
            self.message_queue.insert(0, random.choice(['Au!', 'Ouch..', 'Woot!!', 'Bah!!']))