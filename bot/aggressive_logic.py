import math
import re

class AggressiveAgent:
    def __init__(self, bot_instance):
        self.bot = bot_instance
        self.last_pos = {'x': 0, 'y': 0}
        self.stuck_count = 0

    def get_dist(self, p1, p2):
        return math.sqrt((p1['x'] - p2['x'])**2 + (p1['y'] - p2['y'])**2)

    def run_logic(self, game_state):
        # --- 1. DATA DASAR & ANTI-DEATH ZONE ---
        player = game_state.get('player') or game_state.get('me')
        if not player or player.get('hp', 0) <= 0: return
        
        current_weapon = player.get('weapon', 'Fist')
        enemies = [e for e in game_state.get('enemies', []) if e.get('hp', 0) > 0]
        items = game_state.get('items', [])
        current_region = game_state.get('currentRegion', {})

        if current_region.get('isDeathZone') or current_region.get('warning'):
            self.bot.move_to_safe_zone()
            return

        # --- 2. AUTO-SOLVE RIDDLE (Kembali Ditambahkan) ---
        for msg in game_state.get("recentMessages", []):
            if msg.get("type") == "private":
                content = msg.get("message", "").lower()
                nums = [int(n) for n in re.findall(r'\d+', content)]
                if len(nums) >= 2:
                    ans = str(nums[0] + nums[1]) if "+" in content else str(max(nums))
                    self.bot.whisper(msg["senderId"], ans)

        # --- 3. PRIORITAS: CARI SENJATA (Jika masih Fist) ---
        if current_weapon == 'Fist':
            priority_items = [i for i in items if i.get('type') in ['Katana', 'Sniper', 'Sword', 'Vest']]
            if priority_items:
                best = min(priority_items, key=lambda i: self.get_dist(player, i))
                self.bot.move_to(best['x'], best['y'])
                self.bot.pickup(best['id'])
                self.bot.equip(best['id'])
                return
            else:
                self.bot.move_to_safe_zone() # Cari senjata di wilayah lain
                return

        # --- 4. MANAJEMEN TAS (Sponsor Slot - Kembali Ditambahkan) ---
        raw_inv = game_state.get('inventory', [])
        if len(raw_inv) >= 8:
            for item in raw_inv:
                if item.get('type') not in ['Katana', 'Sniper', 'Medkit', 'Bandage', 'Vest']:
                    self.bot.drop_item(item.get('id'))
                    break

        # --- 5. LOGIKA "THE HYENA" & GUARDIAN (Cari sMoltz) ---
        monsters = game_state.get('visibleMonsters', [])
        guardians = [m for m in monsters if "Guardian" in m.get('type', '')]
        
        if guardians:
            g = guardians[0]
            if enemies: # Jika ada orang lain lagi lawan Guardian, serang orangnya!
                target_enemy = min(enemies, key=lambda e: e.get('hp', 100))
                self.bot.move_to(target_enemy['x'], target_enemy['y'])
                self.bot.attack(target_enemy['id'])
            else: # Jika sepi, habisi Guardian-nya
                self.bot.move_to(g['x'], g['y'])
                self.bot.attack(g['id'])
            return

        # --- 6. SERANGAN PEMAIN (Jika HP > 60) ---
        if enemies and player.get('hp', 100) > 60:
            target = min(enemies, key=lambda e: (e.get('hp', 100) + e.get('def', 0)))
            self.bot.move_to(target['x'], target['y'])
            if self.get_dist(player, target) < 1.5: self.bot.use_skill('all')
            self.bot.attack(target['id'])
            return

        # --- 7. ANTI-STUCK (Kembali Ditambahkan) ---
        if player['x'] == self.last_pos['x'] and player['y'] == self.last_pos['y']:
            self.stuck_count += 1
        else: self.stuck_count = 0
        self.last_pos = {'x': player['x'], 'y': player['y']}
        if self.stuck_count > 2: self.bot.move_to(player['x'] + 2, player['y'] - 1)
        
        self.bot.find_loot()
