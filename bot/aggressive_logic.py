import math
import re

class AggressiveAgent:
    def __init__(self, bot_instance):
        self.bot = bot_instance
        self.last_pos = {'x': 0, 'y': 0}
        self.stuck_count = 0
        self.is_healing_mode = False 

    def get_dist(self, p1, p2):
        return math.sqrt((p1['x'] - p2['x'])**2 + (p1['y'] - p2['y'])**2)

    def run_logic(self, game_state):
        # 1. AMBIL DATA LENGKAP & MONITOR WAKTU
        player = game_state.get('player') or game_state.get('me')
        if not player or player.get('hp', 0) <= 0: return
            
        enemies = [e for e in game_state.get('enemies', []) if e.get('hp', 0) > 0]
        items = game_state.get('items', [])
        raw_inv = game_state.get('inventory', [])
        current_region = game_state.get('currentRegion', {})
        current_hp = player.get('hp', 100)
        current_weapon = player.get('weapon', 'Fist')
        AGENT_ID = player.get('id')

        # === 2. AUTO-SOLVE RIDDLE (PENGHEMAT ENERGI) ===
        for msg in game_state.get("recentMessages", []):
            if msg.get("type") == "private":
                content = msg.get("message", "").lower()
                nums = [int(n) for n in re.findall(r'\d+', content)]
                if len(nums) >= 2:
                    ans = str(nums + nums) if "+" in content else str(max(nums))
                    self.bot.whisper(msg["senderId"], ans)

        # === 3. MANAJEMEN TAS (SPONSOR SLOT) ===
        if len(raw_inv) >= 8:
            for item in raw_inv:
                if item.get('type') not in ['Katana', 'Sniper', 'Medkit', 'Bandage', 'Vest', 'Helmet']:
                    self.bot.drop_item(item.get('id'))
                    break

        # --- 4. PRIORITAS 1: ANTI-DEATH ZONE (LARI DULU!) ---
        if current_region.get('isDeathZone') or current_region.get('warning'):
            self.bot.move_to_safe_zone()
            return

        # --- 5. LOGIKA NINJA: HINDARI PEMAIN (MID-GAME SURVIVAL) ---
        # Jika ada pemain lain dan HP kita belum benar-benar penuh atau masih mid-game, KABUR!
        if enemies and current_hp < 95:
            # Ninja tidak bertarung jika tidak perlu. Cari wilayah Forest atau Ruins untuk sembunyi.
            self.bot.move_to_safe_zone()
            return

        # --- 6. STRATEGI EKONOMI NINJA (HANYA GUARDIAN & LOOT) ---
        target_player = min(enemies, key=lambda e: e.get('hp', 100)) if enemies else None
        
        # A. Prioritas: Ambil Item Dewa kalau lewat
        priority = [i for i in items if i.get('type') in ['Katana', 'Sniper', 'Vest', 'Helmet']]
        if priority:
            best = min(priority, key=lambda i: self.get_dist(player, i))
            self.bot.move_to(best['x'], best['y'])
            self.bot.pickup(best['id'])
            self.bot.equip(best['id'])
            return

        # B. Berburu Guardian (Cari Cuan 600 sMoltz)
        monsters = game_state.get('visibleMonsters', [])
        guardians = [m for m in monsters if "Guardian" in m.get('type', '')]
        if guardians:
            g = guardians[0]
            self.bot.move_to(g['x'], g['y'])
            self.bot.attack(g['id'])
            return

        # --- 7. LOGIKA EKSEKUTOR (HANYA UNTUK TARGET SEKARAT) ---
        if target_player:
            # Ninja hanya keluar menyerang jika musuh HP-nya < 30 (Mudah di-Kill)
            if target_player.get('hp', 100) < 30:
                self.bot.move_to(target_player['x'], target_player['y'])
                if self.get_dist(player, target_player) < 1.5: self.bot.attack(target_player['id'])
                return

        # 8. EKSPLORASI / SEMBUNYI
        self.bot.find_loot()

        # 9. ANTI-STUCK
        if player['x'] == self.last_pos['x'] and player['y'] == self.last_pos['y']:
            self.stuck_count += 1
        else: self.stuck_count = 0
        self.last_pos = {'x': player['x'], 'y': player['y']}
        if self.stuck_count > 2: self.bot.move_to(player['x'] + 2, player['y'] - 1)
