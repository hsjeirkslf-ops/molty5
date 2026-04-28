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
        # 1. DATA DASAR
        player = game_state.get('player') or game_state.get('me')
        if not player or player.get('hp', 0) <= 0: return
            
        enemies = [e for e in game_state.get('enemies', []) if e.get('hp', 0) > 0]
        monsters = game_state.get('visibleMonsters', [])
        guardians = [m for m in monsters if "Guardian" in m.get('type', '')]
        items = game_state.get('items', [])
        current_hp = player.get('hp', 100)
        current_weapon = player.get('weapon', 'Fist')
        AGENT_ID = player.get('id')

        # === 2. AUTO-SOLVE RIDDLE (EP RECOVERY) ===
        for msg in game_state.get("recentMessages", []):
            if msg.get("type") == "private":
                content = msg.get("message", "").lower()
                nums = [int(n) for n in re.findall(r'\d+', content)]
                if len(nums) >= 2:
                    ans = str(nums + nums) if "+" in content else str(max(nums))
                    self.bot.whisper(msg["senderId"], ans)

        # --- 3. PRIORITAS 1: ANTI-DEATH ZONE ---
        current_region = game_state.get('currentRegion', {})
        if current_region.get('isDeathZone') or current_region.get('warning'):
            self.bot.move_to_safe_zone()
            return

        # --- 4. LOGIKA "THE HYENA" (CURI KILL & SMOLTZ) ---
        # Jika ada Guardian DAN ada musuh di wilayah yang sama
        if guardians and enemies:
            target_guardian = guardians[0]
            # Incar musuh yang sedang sibuk memukul Guardian
            target_enemy = min(enemies, key=lambda e: e.get('hp', 100))
            
            # Serang musuhnya dulu agar kita dapat poin Kill
            self.bot.move_to(target_enemy['x'], target_enemy['y'])
            self.bot.attack(target_enemy['id'])
            return

        # --- 5. LOGIKA FINISHING GUARDIAN (SETELAH MUSUH MATI) ---
        if guardians and not enemies:
            g = guardians[0]
            # Jika HP Guardian rendah, langsung habisi
            self.bot.move_to(g['x'], g['y'])
            self.bot.attack(g['id'])
            # Jika ada sMoltz jatuh, ambil!
            for item in items:
                if "smoltz" in item.get('type', '').lower():
                    self.bot.pickup(item['id'])
            return

        # --- 6. LOGIKA SURVIVAL & HINDARI MUSUH SEHAT ---
        if enemies and not guardians and current_hp < 90:
            self.bot.move_to_safe_zone()
            return

        # --- 7. LOOTING ITEM DEWA ---
        priority_items = [i for i in items if i.get('type') in ['Katana', 'Sniper', 'Vest', 'Helmet']]
        if priority_items:
            best = min(priority_items, key=lambda i: self.get_dist(player, i))
            self.bot.move_to(best['x'], best['y'])
            self.bot.pickup(best['id'])
            self.bot.equip(best['id'])
            return

        # 8. EKSPLORASI / CARI GUARDIAN LAIN
        self.bot.find_loot()

        # 9. ANTI-STUCK
        if player['x'] == self.last_pos['x'] and player['y'] == self.last_pos['y']:
            self.stuck_count += 1
        else: self.stuck_count = 0
        self.last_pos = {'x': player['x'], 'y': player['y']}
        if self.stuck_count > 2: self.bot.move_to(player['x'] + 2, player['y'] - 1)
