import os
import json
import math
import time
import re
import random
from collections import Counter
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Union
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
import threading
from concurrent.futures import ThreadPoolExecutor
import logging

logger = logging.getLogger("OpenDotaClient")

TIER_NAMES = {
    1: "Herald",
    2: "Guardian",
    3: "Crusader",
    4: "Archon",
    5: "Legend",
    6: "Ancient",
    7: "Divine",
    8: "Immortal"
}

# Tên viết tắt thông dụng trong cộng đồng Dota 2
HERO_ABBREVIATIONS = {
    "Anti-Mage": "AM",
    "Axe": "Axe",
    "Bane": "Bane",
    "Bloodseeker": "BS",
    "Crystal Maiden": "CM",
    "Drow Ranger": "Drow",
    "Earthshaker": "ES",
    "Juggernaut": "Jugg",
    "Mirana": "Mirana",
    "Morphling": "Morph",
    "Shadow Fiend": "SF",
    "Phantom Lancer": "PL",
    "Puck": "Puck",
    "Pudge": "Pudge",
    "Razor": "Razor",
    "Sand King": "SK",
    "Storm Spirit": "Storm",
    "Sven": "Sven",
    "Tiny": "Tiny",
    "Vengeful Spirit": "Venge",
    "Windranger": "WR",
    "Zeus": "Zeus",
    "Kunkka": "Kunkka",
    "Lina": "Lina",
    "Lion": "Lion",
    "Shadow Shaman": "Shaman",
    "Slardar": "Slardar",
    "Tidehunter": "Tide",
    "Witch Doctor": "WD",
    "Lich": "Lich",
    "Riki": "Riki",
    "Enigma": "Enigma",
    "Tinker": "Tinker",
    "Sniper": "Sniper",
    "Necrophos": "Necro",
    "Warlock": "Warlock",
    "Beastmaster": "BM",
    "Queen of Pain": "QoP",
    "Venomancer": "Veno",
    "Faceless Void": "Void",
    "Wraith King": "WK",
    "Death Prophet": "DP",
    "Phantom Assassin": "PA",
    "Pugna": "Pugna",
    "Templar Assassin": "TA",
    "Viper": "Viper",
    "Luna": "Luna",
    "Dragon Knight": "DK",
    "Dazzle": "Dazzle",
    "Clockwerk": "Clock",
    "Leshrac": "Lesh",
    "Nature's Prophet": "NP",
    "Lifestealer": "LS",
    "Dark Seer": "DS",
    "Clinkz": "Clinkz",
    "Omniknight": "Omni",
    "Enchantress": "Ench",
    "Huskar": "Huskar",
    "Night Stalker": "NS",
    "Broodmother": "Brood",
    "Bounty Hunter": "BH",
    "Weaver": "Weaver",
    "Jakiro": "Jakiro",
    "Batrider": "Bat",
    "Chen": "Chen",
    "Spectre": "Spec",
    "Ancient Apparition": "AA",
    "Doom": "Doom",
    "Ursa": "Ursa",
    "Spirit Breaker": "SB",
    "Gyrocopter": "Gyro",
    "Alchemist": "Alche",
    "Invoker": "Invo",
    "Silencer": "Silencer",
    "Outworld Destroyer": "OD",
    "Outworld Devourer": "OD",
    "Lycan": "Lycan",
    "Brewmaster": "Brew",
    "Shadow Demon": "SD",
    "Lone Druid": "LD",
    "Chaos Knight": "CK",
    "Meepo": "Meepo",
    "Treant Protector": "Treant",
    "Ogre Magi": "Ogre",
    "Undying": "Undying",
    "Rubick": "Rubick",
    "Disruptor": "Disruptor",
    "Nyx Assassin": "Nyx",
    "Naga Siren": "Naga",
    "Keeper of the Light": "KotL",
    "Io": "Io",
    "Visage": "Visage",
    "Slark": "Slark",
    "Medusa": "Dusa",
    "Troll Warlord": "Troll",
    "Centaur Warrunner": "Centaur",
    "Magnus": "Mag",
    "Timbersaw": "Timber",
    "Bristleback": "BB",
    "Tusk": "Tusk",
    "Skywrath Mage": "Sky",
    "Abaddon": "Abaddon",
    "Elder Titan": "ET",
    "Legion Commander": "LC",
    "Techies": "Techies",
    "Ember Spirit": "Ember",
    "Earth Spirit": "Earth Spirit",
    "Underlord": "Underlord",
    "Terrorblade": "TB",
    "Phoenix": "Phoenix",
    "Oracle": "Oracle",
    "Winter Wyvern": "WW",
    "Arc Warden": "Arc",
    "Monkey King": "MK",
    "Dark Willow": "Willow",
    "Pangolier": "Pango",
    "Grimstroke": "Grim",
    "Hoodwink": "Hoodwink",
    "Void Spirit": "Void Spirit",
    "Snapfire": "Snap",
    "Mars": "Mars",
    "Dawnbreaker": "Dawn",
    "Marci": "Marci",
    "Primal Beast": "PB",
    "Muerta": "Muerta",
    "Ringmaster": "Ringmaster",
    "Kez": "Kez"
}

ITEM_NAMES_D2PT = {
    1: "Blink", 41: "Bottle", 36: "Wand", 29: "Boots", 48: "PT", 50: "Phase", 180: "Arcane", 214: "Tranquil", 220: "BoT",
    259: "Kaya", 277: "Bloodstone", 116: "BKB", 609: "Shard", 96: "Shiva", 108: "Aghanim", 114: "Heart", 139: "Butterfly",
    141: "Daedalus", 147: "Manta", 151: "Armlet", 154: "Invis", 158: "Halberd", 160: "Skadi", 166: "Maelstrom", 168: "Deso",
    172: "Mask", 174: "Diffusal", 185: "Drum", 226: "Lotus", 232: "Aether", 235: "Octarine", 236: "DragonLance",
    249: "SilverEdge", 250: "Bloodthorn", 252: "Echo", 254: "Glimmer", 263: "Hurricane", 267: "Vessel",
    271: "HolyLocket", 279: "KayaSange", 286: "Nullifier", 600: "Gleipnir", 603: "MageSlayer", 604: "Falcon",
    640: "EternalShroud", 655: "WindWaker", 1097: "Harpoon", 1107: "Phylactery", 1123: "Khanda", 1124: "Parasma"
}

class OpenDotaClient:
    def __init__(
        self,
        account_id: str = "196931374",
        api_key: Optional[str] = None,
        steam_api_key: Optional[str] = None,
        stratz_api_token: Optional[str] = None,
        tz_offset_hours: int = 7,
        session_gap_hours: float = 5.0
    ):
        self.account_id = str(account_id)
        self.api_key = api_key
        self.steam_api_key = steam_api_key
        self.stratz_api_token = stratz_api_token
        self.tz = timezone(timedelta(hours=tz_offset_hours))
        self.session_gap_hours = session_gap_hours
        
        # Configure robust HTTP session with automatic retries for dropped connections
        self.session = requests.Session()
        retries = Retry(
            total=3,
            connect=3,
            read=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            raise_on_status=False
        )
        adapter = HTTPAdapter(max_retries=retries, pool_connections=10, pool_maxsize=10)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Dota2StreamBot/1.3",
            "Accept": "application/json"
        })
        
        # In-memory caches (preserve stale data on transient network hiccups)
        self._heroes_cache: Dict[int, str] = {}
        self._profile_cache: Optional[Dict[str, Any]] = None
        self._profile_cache_time = 0.0
        self._matches_cache: Optional[List[Dict[str, Any]]] = None
        self._matches_cache_time = 0.0
        self.cache_ttl_profile = 60.0
        self.cache_ttl_matches = 20.0
        self.cache_ttl_player_heroes = 300.0
        self.cache_ttl_player_peers = 300.0
        self.cache_ttl_live = 60.0
        self.cache_ttl_distributions = 86400.0  # 24 hours
        self._player_heroes_cache: Optional[List[Dict[str, Any]]] = None
        self._player_heroes_cache_time = 0.0
        self._player_peers_cache: Optional[List[Dict[str, Any]]] = None
        self._player_peers_cache_time = 0.0
        self._live_cache: Optional[List[Dict[str, Any]]] = None
        self._live_cache_time = 0.0
        self._distributions_cache: Optional[Dict[str, Any]] = None
        self._distributions_cache_time = 0.0
        self.cache_ttl_totals = 86400.0       # 24 hours (1 ngày)
        self.cache_ttl_pros = 86400.0         # 24 hours (1 ngày)
        self.cache_ttl_wl = 86400.0           # 24 hours (1 ngày)
        self._totals_cache: Optional[List[Dict[str, Any]]] = None
        self._totals_cache_time = 0.0
        self._pros_cache: Optional[List[Dict[str, Any]]] = None
        self._pros_cache_time = 0.0
        self._wl_cache: Optional[Dict[str, Any]] = None
        self._wl_cache_time = 0.0
        self._last_funfact_idx: int = -1
        self._funfact_deck: List[int] = []
        self._connapse_cache: Optional[List[Dict[str, Any]]] = None
        self._connapse_cache_time = 0.0
        self.cache_ttl_connapse = 86400.0  # 24 hours
        self._last_connapse_idx: int = -1
        self._connapse_deck: List[int] = []
        self._tworax_deck: List[int] = []
        self._custom_pro_cache: Dict[int, Dict[str, Any]] = {}
        self._custom_pro_cache_time: Dict[int, float] = {}
        self.cache_ttl_custom_pro = 86400.0  # 24 hours
        
        # Cache thống kê Dieback lưu trữ local
        self.dieback_cache_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dieback_cache.json")
        self._dieback_cache: Dict[str, Any] = self._load_dieback_cache()
        
        self._last_refresh_time = 0.0

    def trigger_opendota_refresh(self):
        """Asynchronously notify OpenDota to sync recent matches from Valve."""
        now = time.time()
        if now - self._last_refresh_time > 45.0:
            self._last_refresh_time = now
            def _refresh():
                try:
                    self.session.post(
                        f"https://api.opendota.com/api/players/{self.account_id}/refresh",
                        timeout=5
                    )
                except Exception:
                    pass
            threading.Thread(target=_refresh, daemon=True).start()

    def _api_get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
        url = f"https://api.opendota.com/api/{endpoint.lstrip('/')}"
        p = params.copy() if params else {}
        if self.api_key:
            p["api_key"] = self.api_key
        resp = self.session.get(url, params=p, timeout=12)
        resp.raise_for_status()
        return resp.json()

    def get_hero_name(self, hero_id: int) -> str:
        """Fetch and cache hero names from OpenDota constants."""
        if not self._heroes_cache:
            try:
                data = self._api_get("constants/heroes")
                for hid_str, hero_info in data.items():
                    self._heroes_cache[int(hid_str)] = hero_info.get("localized_name", f"Hero #{hid_str}")
            except Exception:
                return f"Hero #{hero_id}"
        return self._heroes_cache.get(hero_id, f"Hero #{hero_id}")

    def get_hero_short_name(self, hero_id: int) -> str:
        """Get common community abbreviation for hero name (e.g. Outworld Devourer -> OD, Templar Assassin -> TA)."""
        full_name = self.get_hero_name(hero_id)
        return HERO_ABBREVIATIONS.get(full_name, full_name)

    def get_player_data(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Fetch player profile and rank with stale cache fallback."""
        now = time.time()
        if not force_refresh and self._profile_cache and (now - self._profile_cache_time < self.cache_ttl_profile):
            return self._profile_cache

        try:
            data = self._api_get(f"players/{self.account_id}")
            self._profile_cache = data
            self._profile_cache_time = now
            return data
        except Exception as e:
            # Fall back to stale cache if network glitch occurs
            if self._profile_cache:
                logger.warning(f"Lỗi kết nối OpenDota, dùng dữ liệu cache cũ: {e}")
                return self._profile_cache
            raise e

    def _fetch_stratz_matches(self) -> List[Dict[str, Any]]:
        """Fetch real-time matches from STRATZ.com GraphQL API if STRATZ_API_TOKEN is provided."""
        if not self.stratz_api_token:
            return []
        try:
            query = """
            query ($steamAccountId: Long!) {
              player(steamAccountId: $steamAccountId) {
                matches(request: { take: 10 }) {
                  id
                  startDateTime
                  durationSeconds
                  players {
                    steamAccountId
                    heroId
                    isVictory
                    kills
                    deaths
                    assists
                  }
                }
              }
            }
            """
            headers = {
                "Authorization": f"Bearer {self.stratz_api_token}",
                "User-Agent": "STRATZ_API",
                "Content-Type": "application/json"
            }
            payload = {
                "query": query,
                "variables": {"steamAccountId": int(self.account_id)}
            }
            resp = self.session.post("https://api.stratz.com/graphql", json=payload, headers=headers, timeout=8)
            if resp.status_code != 200:
                logger.warning(f"STRATZ API trả về status {resp.status_code}")
                return []
            
            data = resp.json().get("data", {}).get("player", {}) or {}
            raw_matches = data.get("matches", []) or []
            
            parsed_matches = []
            for rm in raw_matches:
                match_id = rm.get("id")
                start_time = rm.get("startDateTime", 0)
                duration = rm.get("durationSeconds", 0)
                
                players = rm.get("players", []) or []
                player_entry = next((p for p in players if str(p.get("steamAccountId")) == self.account_id), None)
                if not player_entry:
                    continue
                
                hero_id = player_entry.get("heroId")
                won = bool(player_entry.get("isVictory", False))
                kills = player_entry.get("kills", 0)
                deaths = player_entry.get("deaths", 0)
                assists = player_entry.get("assists", 0)
                
                # Mock player_slot and radiant_win to remain compatible with OpenDota logic:
                # slot < 128 and radiant_win == won
                parsed_matches.append({
                    "match_id": match_id,
                    "player_slot": 0,
                    "radiant_win": won,
                    "duration": duration,
                    "hero_id": hero_id,
                    "start_time": start_time,
                    "kills": kills,
                    "deaths": deaths,
                    "assists": assists
                })
            return parsed_matches
        except Exception as e:
            logger.warning(f"Lỗi khi gọi STRATZ API: {e}")
            return []

    def _fetch_d2pt_matches(self) -> List[Dict[str, Any]]:
        """Fetch matches from Dota2ProTracker for pro/high MMR players in near real-time."""
        try:
            url = f"https://dota2protracker.com/player/{self.account_id}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            resp = self.session.get(url, headers=headers, timeout=6)
            if resp.status_code != 200:
                return []
            
            pattern = re.compile(
                rf'\{{match_id:(\d+),server_steam_id:[^,]*,lobby_id:[^,]*,lobby_type:[^,]*,clusterId:[^,]*,mmr:(\d+),duration:(\d+),activate_time:(\d+),radiant_win:([01]).*?account_id:{self.account_id},hero_id:(\d+).*?is_radiant:([01]).*?kills:(\d+),deaths:(\d+),assists:(\d+)'
            )
            parsed_matches = []
            txt = resp.text
            for m in pattern.finditer(txt):
                mid, mmr_val, dur, act, r_win, hid, is_rad, k, d, a = m.groups()
                start_idx = m.start()
                end_idx = txt.find('{match_id:', start_idx + 10)
                chunk = txt[start_idx:end_idx] if end_idx != -1 else txt[start_idx:start_idx+30000]

                role_m = re.search(r'role:"?([^",}]+)', chunk)
                pmp_m = re.search(r'pmp:([-\d\.]+)', chunk)
                nw_m = re.search(r'net_worth:(\d+)', chunk)
                gpm_m = re.search(r'gold_per_min:(\d+)', chunk)
                cs_m = re.search(r'last_hits:(\d+)', chunk)

                it_chunk = re.search(r'items:\[(.*?)\]', chunk)
                item_timeline = []
                if it_chunk:
                    for iid, minute, imp in re.findall(r'\{item_id:(\d+),minute:(-?\d+)[^}]*important:(true|false)', it_chunk.group(1)):
                        iid_int = int(iid)
                        min_int = int(minute)
                        if min_int >= 0:
                            iname = ITEM_NAMES_D2PT.get(iid_int)
                            if iname and iname not in ['Bottle', 'Wand', 'Boots', 'PT', 'Phase', 'Arcane']:
                                item_timeline.append(f"{iname} ({min_int}p)")
                        elif iid_int == 609:
                            item_timeline.append(f"Shard ({min_int}p)")

                parsed_matches.append({
                    "match_id": int(mid),
                    "mmr": int(mmr_val) if mmr_val else None,
                    "duration": int(dur),
                    "start_time": int(act),
                    "radiant_win": bool(int(r_win)),
                    "hero_id": int(hid),
                    "player_slot": 0 if int(is_rad) == 1 else 128,
                    "kills": int(k),
                    "deaths": int(d),
                    "assists": int(a),
                    "role": role_m.group(1).strip() if role_m and role_m.group(1).strip() != 'unknown' else None,
                    "pmp": float(pmp_m.group(1)) if pmp_m else None,
                    "net_worth": int(nw_m.group(1)) if nw_m else None,
                    "gold_per_min": int(gpm_m.group(1)) if gpm_m else None,
                    "last_hits": int(cs_m.group(1)) if cs_m else None,
                    "item_timeline": item_timeline[:4]
                })
            return parsed_matches
        except Exception as e:
            logger.debug(f"D2PT fetch error: {e}")
            return []

    def _fetch_steam_matches(self) -> List[Dict[str, Any]]:
        """Fetch real-time matches directly from Valve Steam Web API if STEAM_API_KEY is provided."""
        if not self.steam_api_key:
            return []
        try:
            url = "https://api.steampowered.com/IDOTA2Match_570/GetMatchHistory/v1/"
            params = {
                "key": self.steam_api_key,
                "account_id": self.account_id,
                "matches_requested": 10
            }
            # Use requests directly without 503-retry adapter to prevent freezing
            resp = requests.get(url, params=params, timeout=3)
            if resp.status_code != 200:
                logger.warning(f"Steam Web API (GetMatchHistory) trả về status {resp.status_code} (Máy chủ Valve có thể đang bận/bảo trì).")
                return []
            data = resp.json().get("result", {})
            raw_matches = data.get("matches", [])
            
            parsed_matches = []
            for rm in raw_matches[:5]:
                match_id = rm.get("match_id")
                start_time = rm.get("start_time")
                
                player_entry = next((p for p in rm.get("players", []) if str(p.get("account_id")) == self.account_id), None)
                if not player_entry:
                    continue
                
                hero_id = player_entry.get("hero_id")
                player_slot = player_entry.get("player_slot", 0)
                
                det_url = "https://api.steampowered.com/IDOTA2Match_570/GetMatchDetails/v1/"
                det_resp = requests.get(det_url, params={"key": self.steam_api_key, "match_id": match_id}, timeout=3)
                if det_resp.status_code == 200:
                    d_data = det_resp.json().get("result", {})
                    radiant_win = d_data.get("radiant_win", False)
                    duration = d_data.get("duration", 0)
                    p_detail = next((p for p in d_data.get("players", []) if str(p.get("account_id")) == self.account_id), {})
                    kills = p_detail.get("kills", 0)
                    deaths = p_detail.get("deaths", 0)
                    assists = p_detail.get("assists", 0)
                    parsed_matches.append({
                        "match_id": match_id,
                        "player_slot": player_slot,
                        "radiant_win": radiant_win,
                        "duration": duration,
                        "hero_id": hero_id,
                        "start_time": start_time,
                        "kills": kills,
                        "deaths": deaths,
                        "assists": assists
                    })
            return parsed_matches
        except Exception as e:
            logger.warning(f"Lỗi khi gọi Steam Web API: {e}")
            return []

    def get_recent_matches(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Fetch recent matches: aggregates D2PT, STRATZ, Steam Web API and OpenDota in parallel to pick the most up-to-date data."""
        now = time.time()
        if not force_refresh and self._matches_cache and (now - self._matches_cache_time < self.cache_ttl_matches):
            return self._matches_cache

        self.trigger_opendota_refresh()

        candidates: List[List[Dict[str, Any]]] = []

        def _fetch_od_recent():
            try:
                res = self._api_get(f"players/{self.account_id}/recentMatches")
                return res if isinstance(res, list) else []
            except Exception as e:
                logger.warning(f"Lỗi khi lấy recentMatches từ OpenDota: {e}")
                return []

        def _fetch_od_matches():
            try:
                res = self._api_get(f"players/{self.account_id}/matches", params={"limit": 25})
                return res if isinstance(res, list) else []
            except Exception as e:
                logger.warning(f"Lỗi khi lấy từ OpenDota: {e}")
                return []

        # Chạy song song tất cả các nguồn để giảm tối đa độ trễ (real-time trong 1-2s)
        with ThreadPoolExecutor(max_workers=5) as executor:
            fut_d2pt = executor.submit(self._fetch_d2pt_matches)
            fut_stratz = executor.submit(self._fetch_stratz_matches)
            fut_steam = executor.submit(self._fetch_steam_matches)
            fut_od_rec = executor.submit(_fetch_od_recent)
            fut_od_mat = executor.submit(_fetch_od_matches)

            for fut in [fut_d2pt, fut_stratz, fut_steam, fut_od_rec, fut_od_mat]:
                try:
                    res = fut.result(timeout=5)
                    if res and isinstance(res, list):
                        candidates.append(res)
                except Exception:
                    pass

        # Gộp tất cả các trận đấu từ mọi nguồn theo match_id
        merged: Dict[int, Dict[str, Any]] = {}
        for match_list in candidates:
            for m in match_list:
                mid = m.get("match_id")
                if not mid:
                    continue
                try:
                    mid_int = int(mid)
                except (ValueError, TypeError):
                    continue
                if mid_int not in merged:
                    merged[mid_int] = m
                else:
                    curr = merged[mid_int]
                    curr_has_kda = (curr.get("kills", 0) > 0 or curr.get("deaths", 0) > 0 or curr.get("assists", 0) > 0)
                    new_has_kda = (m.get("kills", 0) > 0 or m.get("deaths", 0) > 0 or m.get("assists", 0) > 0)
                    if not curr_has_kda and new_has_kda:
                        merged[mid_int] = m
                    elif curr.get("duration", 0) == 0 and m.get("duration", 0) > 0:
                        merged[mid_int] = m
                    elif curr.get("radiant_win") is None and m.get("radiant_win") is not None:
                        merged[mid_int] = m
                    
                    # Giữ lại các trường chi tiết bổ sung từ D2PT/STRATZ nếu bản ghi hiện tại chưa có
                    target = merged[mid_int]
                    for field in ["mmr", "role", "pmp", "net_worth", "gold_per_min", "last_hits", "item_timeline"]:
                        if m.get(field) is not None and target.get(field) is None:
                            target[field] = m[field]

        if merged:
            sorted_matches = sorted(
                merged.values(),
                key=lambda x: (self._start_time_epoch(x) or 0, int(x.get("match_id", 0))),
                reverse=True
            )
            self._matches_cache = sorted_matches
            self._matches_cache_time = now
            return sorted_matches

        # Nếu không có nguồn nào trả về, dùng cache cũ
        if self._matches_cache:
            return self._matches_cache

        return []

    @staticmethod
    def _start_time_epoch(match: Dict[str, Any]) -> Optional[float]:
        """Chuẩn hoá start_time về epoch giây (float), hoặc None nếu không đọc được.

        OpenDota/Steam trả về số epoch. STRATZ có thể trả về số epoch hoặc
        chuỗi ISO 8601, nên xử lý cả hai để lọc theo ngày không bị crash.
        """
        value = match.get("start_time")
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                pass
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                return parsed.timestamp()
            except ValueError:
                return None
        return None

    def get_session_matches(self) -> List[Dict[str, Any]]:
        """
        Smart Session Clustering:
        Collects matches played in the current streaming session.
        If there is a gap of > session_gap_hours (e.g. 5 hours) between matches,
        matches prior to that gap belong to a previous session/day and are excluded.
        """
        matches = self.get_recent_matches()
        if not matches:
            return []

        session_matches = []
        for m in matches:
            if not session_matches:
                session_matches.append(m)
            else:
                prev_m = session_matches[-1]
                gap_hours = (prev_m.get("start_time", 0) - m.get("start_time", 0)) / 3600.0
                if gap_hours <= self.session_gap_hours:
                    session_matches.append(m)
                else:
                    break
        return session_matches

    def format_rank(self, rank_tier: Optional[int], leaderboard_rank: Optional[int]) -> str:
        """Parse rank_tier and leaderboard_rank into human-readable string."""
        if not rank_tier:
            return "Chưa xếp hạng (Unranked)"
        
        tier = rank_tier // 10
        stars = rank_tier % 10
        
        if tier == 8:
            if leaderboard_rank:
                return f"Immortal (Top #{leaderboard_rank})"
            return "Immortal"
        
        tier_name = TIER_NAMES.get(tier, f"Tier {tier}")
        if stars > 0:
            return f"{tier_name} [{stars}★]"
        return tier_name

    def get_distributions(self) -> Optional[Dict[str, Any]]:
        """Lấy dữ liệu phân bố rank toàn cầu từ OpenDota /distributions, cache 24h."""
        now = time.time()
        if self._distributions_cache is not None and (now - self._distributions_cache_time < self.cache_ttl_distributions):
            return self._distributions_cache

        try:
            data = self._api_get("distributions")
            if isinstance(data, dict) and "ranks" in data:
                self._distributions_cache = data
                self._distributions_cache_time = now
                return data
        except Exception as e:
            logger.warning(f"Lỗi khi lấy distributions từ OpenDota: {e}")

        return self._distributions_cache

    def get_rank_percentile(self, rank_tier: Optional[int], leaderboard_rank: Optional[int] = None) -> Optional[float]:
        """Tính streamer thuộc Top bao nhiêu % thế giới dựa trên bảng /distributions."""
        if not rank_tier:
            return None

        dist = self.get_distributions()
        if not dist:
            return None

        ranks_data = dist.get("ranks", {})
        total = ranks_data.get("sum", {}).get("count") or 0
        if total <= 0:
            return None

        # Trường hợp Immortal có số Leaderboard
        if rank_tier >= 80 and leaderboard_rank:
            # 4 divisions chính của Valve (EU, CN, SEA, Americas) -> ước lượng rank toàn cầu tối đa ~ leaderboard_rank * 4
            est_global_rank = leaderboard_rank * 4
            top_pct = max(0.01, (est_global_rank / total) * 100.0)
            return top_pct

        rows = {r.get("bin"): r for r in ranks_data.get("rows", []) if r.get("bin") is not None}
        if rank_tier in rows:
            row = rows[rank_tier]
            cum = row.get("cumulative_sum", 0)
            count = row.get("count", 0)
            top_pct = max(0.01, ((total - cum + count) / total) * 100.0)
            return top_pct

        return None

    def get_rank_message(self) -> str:
        """Generate response for !rank command."""
        try:
            player = self.get_player_data()
            profile = player.get("profile", {})
            name = profile.get("personaname", f"Player {self.account_id}")
            rank_tier = player.get("rank_tier")
            leaderboard_rank = player.get("leaderboard_rank")
            
            rank_str = self.format_rank(rank_tier, leaderboard_rank)
            pct = self.get_rank_percentile(rank_tier, leaderboard_rank)

            if pct is not None:
                if pct < 0.1:
                    pct_str = f"Top {pct:.2f}%"
                    better_than_str = f"{100.0 - pct:.2f}%"
                else:
                    pct_str = f"Top {pct:.1f}%"
                    better_than_str = f"{100.0 - pct:.1f}%"
                return f"🏅 Rank của {name}: {rank_str} | Trình độ: {pct_str} thế giới (cao hơn {better_than_str} người chơi)"

            return f"🏅 Rank hiện tại của {name}: {rank_str}"
        except Exception as e:
            logger.error(f"Lỗi trong get_rank_message: {e}", exc_info=True)
            return "⚠️ Máy chủ OpenDota đang phản hồi chậm, bạn vui lòng thử lại sau vài giây!"

    def get_today_message(self) -> str:
        """Generate response for !today command based on the current stream session."""
        try:
            player = self.get_player_data()
            name = player.get("profile", {}).get("personaname", "Streamer")
            now = datetime.now(self.tz)

            # Chỉ tính trận từ 0h hôm nay (theo múi giờ đã cấu hình, mặc định GMT+7).
            # Trước đây hàm chỉ gom theo khoảng cách < 5 tiếng giữa các trận, nên
            # hôm nào chưa đánh thì nó vẫn trả về cả ca hôm qua.
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            today_start_ts = today_start.timestamp()
            session_matches = [
                m for m in self.get_session_matches()
                if (start_ts := self._start_time_epoch(m)) is not None
                and start_ts >= today_start_ts
            ]

            if not session_matches:
                return f"📅 Ca stream hôm nay ({now.strftime('%d/%m')}): {name} chưa có trận đấu nào được ghi nhận."

            wins = 0
            losses = 0
            hero_counts: Dict[str, Dict[str, int]] = {}

            for m in session_matches:
                is_radiant = m.get("player_slot", 0) < 128
                won = (m.get("radiant_win") and is_radiant) or (not m.get("radiant_win") and not is_radiant)
                if won:
                    wins += 1
                else:
                    losses += 1
                
                h_name = self.get_hero_short_name(m.get("hero_id", 0))
                if h_name not in hero_counts:
                    hero_counts[h_name] = {"w": 0, "l": 0}
                if won:
                    hero_counts[h_name]["w"] += 1
                else:
                    hero_counts[h_name]["l"] += 1

            total = wins + losses
            wr = (wins / total * 100) if total > 0 else 0

            latest = session_matches[0]
            lat_radiant = latest.get("player_slot", 0) < 128
            lat_won = (latest.get("radiant_win") and lat_radiant) or (not latest.get("radiant_win") and not lat_radiant)
            lat_hero = self.get_hero_short_name(latest.get("hero_id", 0))
            lat_res = "Thắng ✅" if lat_won else "Thua ❌"
            lat_kda = f"{latest.get('kills', 0)}/{latest.get('deaths', 0)}/{latest.get('assists', 0)}"

            # Thêm [Avg MMR 7.2k] nếu có
            mmr_str = ""
            if latest.get("mmr"):
                mmr_val = float(latest["mmr"]) / 1000.0
                mmr_str = f" [Avg MMR {mmr_val:.1f}k]"

            base_msg = (
                f"🔥 Ca hôm nay ({now.strftime('%d/%m')}): {wins}W - {losses}L ({wr:.1f}%) | "
                f"Vừa xong: {lat_hero} ({lat_kda}) {lat_res}{mmr_str} | Tướng: "
            )

            # Dynamically include abbreviated heroes up to 185 chars, append '...' if truncated
            hero_items = [f"{h} ({s['w']}W-{s['l']}L)" for h, s in hero_counts.items()]
            included_heroes = []
            has_more = False

            for item in hero_items:
                max_len = 182 if (len(included_heroes) + 1 < len(hero_items)) else 185
                test_str = ", ".join(included_heroes + [item])
                if len(base_msg + test_str) <= max_len:
                    included_heroes.append(item)
                else:
                    has_more = True
                    break

            if not included_heroes:
                included_heroes = hero_items[:1]

            hero_str = ", ".join(included_heroes)
            if has_more:
                hero_str += "..."

            return base_msg + hero_str
        except Exception as e:
            logger.error(f"Lỗi trong get_today_message: {e}", exc_info=True)
            return "⚠️ Máy chủ OpenDota đang phản hồi chậm, bạn vui lòng thử lại sau vài giây!"

    def get_last_message(self) -> str:
        """Generate response for !last / !chitiet command: thông số chi tiết trận vừa đánh xong."""
        try:
            matches = self.get_recent_matches()
            if not matches:
                return "⚠️ Chưa có trận đấu nào gần đây được ghi nhận."

            latest = matches[0]
            hero_name = self.get_hero_short_name(latest.get("hero_id", 0))
            is_radiant = latest.get("player_slot", 0) < 128
            won = (latest.get("radiant_win") and is_radiant) or (not latest.get("radiant_win") and not is_radiant)
            res_str = "Thắng ✅" if won else "Thua ❌"
            kda = f"{latest.get('kills', 0)}/{latest.get('deaths', 0)}/{latest.get('assists', 0)}"

            dur_sec = latest.get("duration", 0)
            dur_str = f" ({dur_sec // 60}p)" if dur_sec else ""

            # Role / Vị trí
            role_part = ""
            if latest.get("role"):
                r = latest.get("role").lower()
                if "pos 1" in r:
                    role_str = "Pos 1 Carry"
                elif "pos 2" in r:
                    role_str = "Pos 2 Mid"
                elif "pos 3" in r:
                    role_str = "Pos 3 Off"
                elif "pos 4" in r:
                    role_str = "Pos 4"
                elif "pos 5" in r:
                    role_str = "Pos 5"
                else:
                    role_str = latest.get("role")
                role_part = f" ({role_str})"

            # Avg MMR
            mmr_part = ""
            if latest.get("mmr"):
                mmr_val = float(latest["mmr"]) / 1000.0
                mmr_part = f" [Avg MMR {mmr_val:.1f}k]"

            # PMP (Player Match Performance) giải thích rõ ràng cho khán giả
            pmp_part = ""
            if latest.get("pmp") is not None:
                pmp_val = float(latest["pmp"])
                if pmp_val >= 15.0:
                    desc = "Gánh team 🔥"
                elif pmp_val >= 0.0:
                    desc = "Tròn vai 👍"
                elif pmp_val >= -10.0:
                    desc = "Khó thở ⚠️"
                else:
                    desc = "Dưới phong độ 📉"
                sign = "+" if pmp_val > 0 else ""
                pmp_part = f" | Phong độ: {sign}{pmp_val:.1f} (D2PT chấm: {desc})"

            farm_items = []
            if latest.get("net_worth"):
                nw_k = float(latest["net_worth"]) / 1000.0
                gpm_str = f" ({latest['gold_per_min']} GPM)" if latest.get("gold_per_min") else ""
                farm_items.append(f"Net: {nw_k:.1f}k{gpm_str}")
            if latest.get("last_hits") is not None:
                farm_items.append(f"{latest['last_hits']} CS")

            farm_part = (" | " + ", ".join(farm_items)) if farm_items else ""

            items_part = ""
            if latest.get("item_timeline"):
                items_part = " | Đồ: " + ", ".join(latest["item_timeline"])

            msg = f"📖 Trận vừa xong: {hero_name}{role_part} {res_str}{dur_str}{mmr_part} | KDA: {kda}{pmp_part}{farm_part}{items_part}"

            # YouTube chat giới hạn 200 ký tự. Đảm bảo <= 195 ký tự:
            if len(msg) > 195:
                # Bỏ bớt farm_part để ưu tiên KDA + PMP + Items
                msg_compact = f"📖 Trận vừa xong: {hero_name}{role_part} {res_str}{dur_str}{mmr_part} | KDA: {kda}{pmp_part}{items_part}"
                if len(msg_compact) <= 195:
                    return msg_compact
                if latest.get("item_timeline"):
                    short_items = " | Đồ: " + ", ".join(latest["item_timeline"][:2])
                    msg_compact = f"📖 Trận vừa xong: {hero_name}{role_part} {res_str}{dur_str}{mmr_part} | KDA: {kda}{pmp_part}{short_items}"
                    if len(msg_compact) <= 195:
                        return msg_compact
                return msg[:192] + "..."

            return msg
        except Exception as e:
            logger.error(f"Lỗi trong get_last_message: {e}", exc_info=True)
            return "⚠️ Máy chủ đang phản hồi chậm, bạn vui lòng thử lại sau vài giây!"

    @staticmethod
    def _is_win(match: Dict[str, Any]) -> bool:
        """Trận này streamer thắng hay thua (dựa vào player_slot / radiant_win)."""
        is_radiant = match.get("player_slot", 0) < 128
        return bool((match.get("radiant_win") and is_radiant) or (not match.get("radiant_win") and not is_radiant))

    def get_streak_message(self) -> str:
        """Generate response for !streak / !chuoi: chuỗi thắng/thua hiện tại."""
        try:
            matches = self.get_recent_matches()
            if not matches:
                return "⚠️ Không tìm thấy trận đấu nào gần đây."

            latest = matches[0]
            won_first = self._is_win(latest)
            streak = 0
            for m in matches:
                if self._is_win(m) == won_first:
                    streak += 1
                else:
                    break

            hero = self.get_hero_short_name(latest.get("hero_id", 0))
            kda = f"{latest.get('kills', 0)}/{latest.get('deaths', 0)}/{latest.get('assists', 0)}"
            if won_first:
                return f"🔥 Đang thắng {streak} trận liên tiếp | Trận gần nhất: {hero} ({kda})"
            return f"💀 Đang thua {streak} trận liên tiếp | Trận gần nhất: {hero} ({kda})"
        except Exception as e:
            logger.error(f"Lỗi trong get_streak_message: {e}", exc_info=True)
            return "⚠️ Máy chủ OpenDota đang phản hồi chậm, bạn vui lòng thử lại sau vài giây!"

    def get_recent_message(self, count: int = 10) -> str:
        """Generate response for !recent / !5tran: kết quả các trận gần nhất."""
        try:
            matches = self.get_recent_matches()
            if not matches:
                return "⚠️ Không tìm thấy trận đấu nào gần đây."

            recent = matches[:count]
            # Hiển thị theo thứ tự thời gian (trận cũ trước, trận mới sau)
            # để khán giả đọc xu hướng từ trái sang phải.
            results = ["W" if self._is_win(m) else "L" for m in reversed(recent)]
            wins = results.count("W")
            return f"📊 {len(recent)} trận gần nhất: {' '.join(results)} ({wins}W-{len(recent) - wins}L)"
        except Exception as e:
            logger.error(f"Lỗi trong get_recent_message: {e}", exc_info=True)
            return "⚠️ Máy chủ OpenDota đang phản hồi chậm, bạn vui lòng thử lại sau vài giây!"

    def get_player_heroes(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Tính thống kê tướng trong `limit` trận gần nhất (mặc định 100), cached 5 phút.

        Không dùng endpoint /players/{account_id}/heroes nữa, vì endpoint đó
        trả về thống kê CẢ ĐỜI (không giới hạn số trận). Thay vào đó lấy
        100 trận gần nhất từ /players/{account_id}/matches rồi tự đếm
        số trận / số trận thắng theo từng tướng. Dùng riêng OpenDota ở đây
        (không dùng get_recent_matches) vì STRATZ/Steam trong code hiện tại
        chỉ trả về 10 trận, không đủ 100.
        """
        now = time.time()
        if self._player_heroes_cache and (now - self._player_heroes_cache_time < self.cache_ttl_player_heroes):
            return self._player_heroes_cache
        try:
            data = self._api_get(f"players/{self.account_id}/matches", params={"limit": limit})
            if not isinstance(data, list):
                return []
            counts: Dict[int, Dict[str, int]] = {}
            for m in data[:limit]:
                hero_id = m.get("hero_id")
                if not hero_id:
                    continue
                hero_id = int(hero_id)
                entry = counts.setdefault(hero_id, {"hero_id": hero_id, "games": 0, "win": 0})
                entry["games"] += 1
                if self._is_win(m):
                    entry["win"] += 1
            result = list(counts.values())
            self._player_heroes_cache = result
            self._player_heroes_cache_time = now
            return result
        except Exception as e:
            logger.warning(f"Lỗi khi lấy thống kê tướng từ OpenDota: {e}")
            if self._player_heroes_cache:
                return self._player_heroes_cache
        return []

    def get_heroes_message(self) -> str:
        """Generate response for !heroes / !besthero: tướng tủ trong 100 trận gần nhất."""
        try:
            heroes = self.get_player_heroes()
            if not heroes:
                return "⚠️ Không lấy được thống kê tướng, bạn vui lòng thử lại sau vài giây!"

            played = [h for h in heroes if (h.get("games") or 0) > 0]
            if not played:
                return "⚠️ Không lấy được thống kê tướng, bạn vui lòng thử lại sau vài giây!"

            top = sorted(played, key=lambda h: h.get("games", 0), reverse=True)[:3]
            parts = []
            for h in top:
                games = h.get("games", 0)
                wins = h.get("win", 0)
                wr = (wins / games * 100) if games else 0
                parts.append(f"{self.get_hero_short_name(h.get('hero_id', 0))} ({games} trận, {wr:.0f}%)")
            return "🏆 Tướng tủ (100 trận gần nhất): " + " | ".join(parts)
        except Exception as e:
            logger.error(f"Lỗi trong get_heroes_message: {e}", exc_info=True)
            return "⚠️ Máy chủ OpenDota đang phản hồi chậm, bạn vui lòng thử lại sau vài giây!"

    def get_player_peers(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Lấy danh sách người chơi cùng trong `limit` trận gần nhất, cached 5 phút.

        Endpoint /players/{account_id}/peers mặc định trả về thống kê CẢ ĐỜI,
        nhưng nó nhận tham số `limit` = số trận gần nhất đem ra tính
        (theo tài liệu OpenDota API). Đã kiểm chứng live 2026-11-06 trên
        account 196931374: /peers không tham số trả về top with_games 668 trận,
        còn /peers?limit=50 chỉ trả về 10 người, top with_games 3 trận; /peers?limit=100 trả về 34 người, 15,8 KB, ~1,8 giây — không nặng hơn đáng kể.
        Chỉ 1 request, không cần tải chi tiết từng trận.
        """
        now = time.time()
        if self._player_peers_cache and (now - self._player_peers_cache_time < self.cache_ttl_player_peers):
            return self._player_peers_cache
        try:
            data = self._api_get(f"players/{self.account_id}/peers", params={"limit": limit})
            if isinstance(data, list):
                self._player_peers_cache = data
                self._player_peers_cache_time = now
                return data
        except Exception as e:
            logger.warning(f"Lỗi khi lấy danh sách duo từ OpenDota: {e}")
            if self._player_peers_cache:
                return self._player_peers_cache
        return []

    def get_mate_message(self) -> str:
        """Generate response for !mate: hay duo với ai trong 100 trận gần nhất.

        Chỉ tính trận chơi CÙNG đội (with_games / with_win). Endpoint peers
        còn trả về games/win tổng (cả cùng đội lẫn đối đầu) và against_games,
        nên phải dùng đúng trường with_* chứ không dùng games/win.
        """
        try:
            peers = self.get_player_peers()
            if not peers:
                return "⚠️ Không lấy được danh sách duo, bạn vui lòng thử lại sau vài giây!"
            duo = [p for p in peers if (p.get("with_games") or 0) > 0]
            if not duo:
                return "⚠️ Không tìm thấy ai duo cùng trong 100 trận gần nhất."
            top = sorted(duo, key=lambda p: p.get("with_games", 0), reverse=True)[:3]
            parts = []
            for p in top:
                games = p.get("with_games", 0)
                wins = p.get("with_win", 0)
                # Hiện số trận thắng (vd: 8W) thay vì % winrate, vì số trận
                # duo trong 100 trận gần nhất khá ít nên % dễ gây hiểu lầm.
                name = p.get("personaname") or f"Player {p.get('account_id', 0)}"
                parts.append(f"{name} ({games} trận, {wins}W)")
            return "👥 Hay duo với (100 trận gần nhất): " + " | ".join(parts)
        except Exception as e:
            logger.error(f"Lỗi trong get_mate_message: {e}", exc_info=True)
            return "⚠️ Máy chủ OpenDota đang phản hồi chậm, bạn vui lòng thử lại sau vài giây!"

    def get_live_game(self) -> Optional[Dict[str, Any]]:
        """Tìm trận đang diễn ra của player trong OpenDota /live, cached 60 giây.

        OpenDota KHÔNG có endpoint trận live theo player. GET /live chỉ trả
        về top 100 trận đang diễn ra, nên phải quét từng trận và tìm
        account_id trong danh sách players[]. Trả về None nếu không thấy —
        lưu ý: không thấy trong /live không đồng nghĩa là không đang đánh,
        vì trận rank thấp có thể không lọt top 100.

        BẪY ĐÃ GẶP 2026-11-06: /live GIỮ LẠI trận đã kết thúc rất lâu sau
        khi nó xong (trận 9078301405 xong lúc ~18:07 mà tới 18:46 vẫn còn
        trong feed, game_time đóng băng ở 2049). Một player có thể xuất
        hiện trong 2 trận cùng lúc trong feed, nên KHÔNG được lấy trận đầu
        tiên tìm thấy. Cách lọc: trong các trận có player, chọn trận có
        last_update_time mới nhất (trận đang đánh được cập nhật liên tục,
        trận xong thì đóng băng); nếu trận mới nhất đó đã quá 300 giây
        không cập nhật thì coi như đã kết thúc. deactivate_time không dùng
        được vì nó vẫn = 0 ngay cả với trận đã xong.
        """
        now = time.time()
        if self._live_cache is not None and (now - self._live_cache_time < self.cache_ttl_live):
            games = self._live_cache
        else:
            try:
                data = self._api_get("live")
                if not isinstance(data, list):
                    return None
                self._live_cache = data
                self._live_cache_time = now
                games = data
            except Exception as e:
                logger.warning(f"Lỗi khi lấy danh sách trận live từ OpenDota: {e}")
                games = self._live_cache or []
        try:
            my_id = int(self.account_id)
        except (TypeError, ValueError):
            return None
        matches = [g for g in games
                   if any(p.get("account_id") == my_id for p in g.get("players") or [])]
        if not matches:
            return None
        # Trận đang đánh là trận được cập nhật gần nhất; trận đã xong thì
        # last_update_time đóng băng và tụt lại phía sau.
        best = max(matches, key=lambda g: (g.get("last_update_time") or 0,
                                            g.get("activate_time") or 0))
        last_update = best.get("last_update_time") or 0
        if last_update and (now - last_update > 300):
            logger.warning(f"Trận live của player {my_id} đã {int(now - last_update)}s không cập nhật, coi như đã kết thúc.")
            return None
        return best

    @staticmethod
    def estimate_win_pct(my_lead: int, game_time: int, kill_diff: int) -> int:
        """Ước tính tỉ lệ thắng của đội streamer, theo công thức heuristic.

        z = 6 * L / (2250 * t) * 30 / (30 + t) + 0.02 * D, P = 1/(1+e^-z),
        kẹp 5-95%. L = chênh vàng theo góc streamer, t = số phút đã đấu,
        D = chênh kill. Vàng được chia cho tổng net worth ước tính của
        một team (5 người x ~450 vàng/phút x t) rồi nhân thêm hệ số
        30/(30+t) vì càng về late vàng càng mất giá (đồ đầy slot, một
        combat là lật được trận). Phần kill không giảm theo thời gian vì
        kill về late càng có giá (thời gian hồi sinh dài).
        Đây là ước tính thô, KHÔNG phải dự đoán của Dota Plus (đóng nguồn)
        và /live không có trụ, XP, buyback hay đồ từng người.
        """
        t = max(float(game_time) / 60.0, 1.0)
        z = 6.0 * my_lead / (2250.0 * t) * (30.0 / (30.0 + t)) + 0.02 * kill_diff
        pct = 100.0 / (1.0 + math.exp(-z))
        return int(max(5, min(95, round(pct))))

    def get_live_message(self) -> str:
        """Generate response for !live: trận đang diễn ra của streamer.

        Theo yêu cầu của user, KHÔNG hiện tướng, tỉ số hay số người xem.
        Chỉ trả về phút thi đấu + tỉ lệ thắng ước tính (xem
        estimate_win_pct) + chênh vàng theo góc streamer, và, nếu có,
        tên pro (is_pro) cùng team / đối đầu lấy từ dữ liệu /live.
        Dữ liệu trễ ~120 giây (delay xem spectate).
        """
        try:
            game = self.get_live_game()
            if not game:
                return "⚠️ Không thấy streamer trong top 100 trận live của OpenDota — có thể đang đánh nhưng trận không lọt top 100."
            players = game.get("players") or []
            me = next((p for p in players if p.get("account_id") == int(self.account_id)), None)
            if not me:
                return "⚠️ Không thấy streamer trong top 100 trận live của OpenDota — có thể đang đánh nhưng trận không lọt top 100."
            game_time = int(game.get("game_time") or 0)
            if game_time < 0:
                game_time = 0
            clock = f"{game_time // 60}:{game_time % 60:02d}"
            radiant_score = game.get("radiant_score") or 0
            dire_score = game.get("dire_score") or 0
            # radiant_lead > 0: Radiant dẫn vàng. Đổi sang góc nhìn của streamer.
            lead = int(game.get("radiant_lead") or 0)
            is_radiant = (me.get("team") == 0)
            my_lead = lead if is_radiant else -lead
            kill_diff = (radiant_score - dire_score) if is_radiant else (dire_score - radiant_score)
            win_pct = self.estimate_win_pct(my_lead, game_time, kill_diff)
            # Chênh vàng theo góc streamer (radiant_lead đã đổi dấu ở trên).
            # Hiện dạng "Dẫn 12k vàng" / "Kém 5k vàng", dưới 1k thì hiện số vàng thô.
            if my_lead == 0:
                gold_part = "Hòa vàng"
            else:
                abs_lead = abs(my_lead)
                lead_str = f"{abs_lead // 1000}k" if abs_lead >= 1000 else f"{abs_lead}"
                gold_part = f"Dẫn {lead_str} vàng" if my_lead > 0 else f"Kém {lead_str} vàng"
            msg = f"🔴 Đang đánh ({clock}): ước tính thắng ~{win_pct}% | {gold_part}"
            # Pro trong trận (is_pro từ /live). Rất hiếm nên chỉ hiện khi có.
            my_team = me.get("team")
            pros_mine = [p.get("name") for p in players
                         if p.get("is_pro") and p.get("team") == my_team and p.get("name")]
            pros_opp = [p.get("name") for p in players
                        if p.get("is_pro") and p.get("team") != my_team and p.get("name")]
            if pros_mine:
                msg += " | Pro cùng team: " + ", ".join(pros_mine)
            if pros_opp:
                msg += " | Pro đối đầu: " + ", ".join(pros_opp)
            return msg
        except Exception as e:
            logger.error(f"Lỗi trong get_live_message: {e}", exc_info=True)
            return "⚠️ Máy chủ OpenDota đang phản hồi chậm, bạn vui lòng thử lại sau vài giây!"

    def get_player_totals(self) -> List[Dict[str, Any]]:
        """Lấy dữ liệu thống kê sự nghiệp từ OpenDota /players/{id}/totals, cache 24h."""
        now = time.time()
        if self._totals_cache is not None and (now - self._totals_cache_time < self.cache_ttl_totals):
            return self._totals_cache

        try:
            data = self._api_get(f"players/{self.account_id}/totals")
            if isinstance(data, list):
                self._totals_cache = data
                self._totals_cache_time = now
                return data
        except Exception as e:
            logger.warning(f"Lỗi khi lấy totals từ OpenDota: {e}")

        return self._totals_cache or []

    def get_player_wl(self) -> Dict[str, Any]:
        """Lấy tổng số trận thắng/thua sự nghiệp từ OpenDota /players/{id}/wl, cache 24h."""
        now = time.time()
        if self._wl_cache is not None and (now - self._wl_cache_time < self.cache_ttl_wl):
            return self._wl_cache

        try:
            data = self._api_get(f"players/{self.account_id}/wl")
            if isinstance(data, dict):
                self._wl_cache = data
                self._wl_cache_time = now
                return data
        except Exception as e:
            logger.warning(f"Lỗi khi lấy wl từ OpenDota: {e}")

        return self._wl_cache or {}

    def get_player_pros(self) -> List[Dict[str, Any]]:
        """Lấy toàn bộ danh sách Pro Player từng thi đấu cùng hoặc đối đầu từ OpenDota, cache 24h."""
        now = time.time()
        if self._pros_cache is not None and (now - self._pros_cache_time < self.cache_ttl_pros):
            return self._pros_cache

        try:
            data = self._api_get(f"players/{self.account_id}/pros")
            if isinstance(data, list):
                self._pros_cache = data
                self._pros_cache_time = now
                return data
        except Exception as e:
            logger.warning(f"Lỗi khi lấy pros từ OpenDota: {e}")

        return self._pros_cache or []

    def get_custom_pro_stats(self, other_account_id: int) -> Optional[Dict[str, int]]:
        """Calculate match stats against a specific player not listed in OpenDota /pros."""
        now = time.time()
        if (
            other_account_id in self._custom_pro_cache
            and (now - self._custom_pro_cache_time.get(other_account_id, 0) < self.cache_ttl_custom_pro)
        ):
            return self._custom_pro_cache[other_account_id]

        try:
            matches = self._api_get(f"players/{self.account_id}/matches", params={"included_account_id": str(other_account_id)})
            if not isinstance(matches, list) or not matches:
                return None

            with_cnt = with_win = against_cnt = against_win = 0
            for m in matches:
                my_slot = m.get("player_slot", 0)
                my_rad = my_slot < 128
                rad_win = m.get("radiant_win", False)
                my_win = (rad_win and my_rad) or (not rad_win and not my_rad)
                heroes = m.get("heroes") or {}
                other_slot = None
                for s_str, p in heroes.items():
                    if str(p.get("account_id")) == str(other_account_id):
                        other_slot = int(s_str)
                        break
                if other_slot is not None:
                    other_rad = other_slot < 128
                    if my_rad == other_rad:
                        with_cnt += 1
                        if my_win:
                            with_win += 1
                    else:
                        against_cnt += 1
                        if my_win:
                            against_win += 1

            stats = {
                "games": with_cnt + against_cnt,
                "with_games": with_cnt,
                "with_win": with_win,
                "against_games": against_cnt,
                "against_win": against_win,
            }
            self._custom_pro_cache[other_account_id] = stats
            self._custom_pro_cache_time[other_account_id] = now
            return stats
        except Exception as e:
            logger.warning(f"Lỗi khi tính thống kê custom pro cho {other_account_id}: {e}")
            return self._custom_pro_cache.get(other_account_id)

    def get_career_message(self) -> str:
        """Generate response for !career / !totals: thống kê toàn bộ sự nghiệp."""
        try:
            player = self.get_player_data()
            name = player.get("profile", {}).get("personaname", "Streamer")

            wl = self.get_player_wl()
            w = wl.get("win", 0)
            l = wl.get("lose", 0)
            tot_matches = w + l
            wr = (w / tot_matches * 100.0) if tot_matches else 0.0

            totals_list = self.get_player_totals()
            totals = {t["field"]: t for t in totals_list}

            dur_secs = totals.get("duration", {}).get("sum", 0)
            hours = int(dur_secs // 3600)
            days = hours // 24

            kills = int(totals.get("kills", {}).get("sum", 0))
            assists = int(totals.get("assists", {}).get("sum", 0))
            hero_dmg = totals.get("hero_damage", {}).get("sum", 0)
            dmg_mil = int(hero_dmg // 1000000)

            def _fmt(n: int) -> str:
                return f"{n:,}".replace(",", ".")

            return (
                f"📜 Sự nghiệp Dota 2 của {name}: {_fmt(tot_matches)} trận "
                f"({_fmt(w)}W-{_fmt(l)}L, {wr:.1f}%) | {_fmt(hours)} giờ chơi ({days} ngày đêm) | "
                f"{_fmt(kills)} Kills, {_fmt(assists)} Assists | {dmg_mil} Triệu sát thương!"
            )
        except Exception as e:
            logger.error(f"Lỗi trong get_career_message: {e}", exc_info=True)
            return "⚠️ Máy chủ OpenDota đang phản hồi chậm, bạn vui lòng thử lại sau vài giây!"

    def _draw_from_deck(self, deck: List[int], total_items: int) -> int:
        """
        Shuffle-bag (deck of cards) algorithm:
        Đảm bảo phân bố đều 100% giữa các sự kiện, không bao giờ bị thiên vị hay lặp lại
        một vài câu cho tới khi tất cả các câu trong danh sách đều đã xuất hiện đúng 1 lần.
        """
        if not deck:
            new_deck = list(range(total_items))
            random.shuffle(new_deck)
            deck.extend(new_deck)
        return deck.pop()

    def get_funfact_message(self) -> str:
        """Generate response for !funfact / !ditat: ngẫu nhiên 1 trong 10 fact thú vị độc đáo."""
        try:
            player = self.get_player_data()
            raw_name = player.get("profile", {}).get("personaname", "Streamer")
            name = (raw_name[:25] + "..") if len(raw_name) > 28 else raw_name

            totals_list = self.get_player_totals()
            if not totals_list:
                return "⚠️ Hiện chưa tải được thống kê funfact từ OpenDota, vui lòng thử lại sau!"
            totals = {t["field"]: t for t in totals_list}

            def _fmt(n: int) -> str:
                return f"{n:,}".replace(",", ".")

            couriers = int(totals.get("courier_kills", {}).get("sum", 0))
            courier_matches = int(totals.get("courier_kills", {}).get("n", totals.get("kills", {}).get("n", 1)))
            matches_per_courier = round(courier_matches / max(1, couriers), 1)

            apm = totals.get("actions_per_min", {}).get("sum", 0) / max(1, totals.get("actions_per_min", {}).get("n", 1))
            pings_sum = int(totals.get("pings", {}).get("sum", 0))
            pings_avg = pings_sum / max(1, totals.get("pings", {}).get("n", 1))

            rapiers = int(totals.get("purchase_rapier", {}).get("sum", 0))
            gems = int(totals.get("purchase_gem", {}).get("sum", 0))

            deaths = int(totals.get("deaths", {}).get("sum", 0))
            respawn_hours = int((deaths * 40) // 3600)
            respawn_days = int(respawn_hours // 24)

            last_hits = int(totals.get("last_hits", {}).get("sum", 0))
            neutrals = int(totals.get("neutral_kills", {}).get("sum", 0))
            total_creeps = last_hits + neutrals
            hero_dmg = totals.get("hero_damage", {}).get("sum", 0)
            dmg_mil = int(hero_dmg // 1000000)
            rosh_count = max(1, int(hero_dmg // 7500))

            stuns_sec = int(totals.get("stuns", {}).get("sum", 0))
            stuns_hours = round(stuns_sec / 3600.0, 1)
            stuns_days = round(stuns_hours / 24.0, 1)

            towers = int(totals.get("tower_kills", {}).get("sum", 0))
            if towers >= 10000:
                tower_desc = "chính thức vượt mốc kỷ lục 10.000 công trình khiến thợ xây thất nghiệp!"
            else:
                tower_desc = f"chỉ còn {10000 - towers} trụ nữa là cán mốc 10.000 công trình!"

            tps = int(totals.get("purchase_tpscroll", {}).get("sum", 0))
            tp_gold_mil = round((tps * 100) / 1000000, 1)
            denies = int(totals.get("denies", {}).get("sum", 0))

            obs = int(totals.get("purchase_ward_observer", {}).get("sum", 0))
            sent = int(totals.get("purchase_ward_sentry", {}).get("sum", 0))
            total_wards = obs + sent

            dur_secs = totals.get("duration", {}).get("sum", 0)
            hours = int(dur_secs // 3600)
            days = hours // 24
            kills = int(totals.get("kills", {}).get("sum", 0))
            assists = int(totals.get("assists", {}).get("sum", 0))
            kda_avg = totals.get("kda", {}).get("sum", 0) / max(1, totals.get("kda", {}).get("n", 1))

            facts = [
                f"🎭 Fun fact: 🪓 {name} đã đồ sát {_fmt(couriers)} con gà (courier)! Cứ trung bình ~{matches_per_courier:.0f} trận lại có 1 shipper xấu số bay màu.",
                f"🎭 Fun fact: ⚡ {name} có tốc độ tay ~{apm:.0f} APM! Đã ping map {_fmt(pings_sum)} lần ({pings_avg:.0f} ping/trận) — mòn cả màng nhĩ đồng đội.",
                f"🎭 Fun fact: 🗡️ {name} đã {rapiers} lần all-in mua Thánh Kiếm Rapier và {gems} lần vác Gem soi tàng hình! Tinh thần không ngại rớt kiếm.",
                f"🎭 Fun fact: 💀 {name} đã {_fmt(deaths)} lần lên bảng đếm số! Ước tính mất ~{_fmt(respawn_hours)} giờ ({respawn_days} ngày đêm) chỉ để ngắm màn hình đen trắng.",
                f"🎭 Fun fact: 💥 {name} đã farm {_fmt(total_creeps)} lính và quái rừng! Gây {dmg_mil} Triệu sát thương hero — đủ tiễn {_fmt(rosh_count)} con Roshan lên bảng!",
                f"🎭 Fun fact: ⏳ {name} đã stun đối thủ tổng cộng {_fmt(stuns_sec)} giây (~{stuns_hours} giờ)! Bắt đối phương đứng im bất động suốt {stuns_days} ngày liên tục.",
                f"🎭 Fun fact: 🏛️ {name} đích thị là máy xúc khi san phẳng {_fmt(towers)} trụ đối phương — {tower_desc}",
                f"🎭 Fun fact: 📜 {name} đã mua {_fmt(tps)} cuộn giấy TP Scroll (~{tp_gold_mil:.1f} triệu vàng tiền xe ôm) và tự tay chối bỏ (deny) {_fmt(denies)} lính đồng minh.",
                f"🎭 Fun fact: 👁️ {name} đã cắm tổng cộng {_fmt(total_wards)} cây mắt ({_fmt(obs)} mắt xanh, {_fmt(sent)} mắt tím) — đủ thắp sáng rực cả bản đồ!",
                f"🎭 Fun fact: ⏱️ {name} cống hiến {_fmt(hours)} giờ ({days} ngày đêm) cho Dota 2! Bỏ túi {_fmt(kills)} Kills, {_fmt(assists)} Assists với KDA trung bình {kda_avg:.2f}."
            ]

            chosen_idx = self._draw_from_deck(self._funfact_deck, len(facts))
            return facts[chosen_idx]
        except Exception as e:
            logger.error(f"Lỗi trong get_funfact_message: {e}", exc_info=True)
            return "⚠️ Máy chủ OpenDota đang phản hồi chậm, bạn vui lòng thử lại sau vài giây!"

    def get_connapse_message(self) -> str:
        """Generate response for !connapse: funfact về cặp đôi streamer & tri kỷ connapse (Account ID: 968755756)."""
        try:
            connapse_id = "968755756"
            now = time.time()
            if self._connapse_cache is not None and (now - self._connapse_cache_time < self.cache_ttl_connapse):
                matches = self._connapse_cache
            else:
                matches = self._api_get(f"players/{self.account_id}/matches", params={"included_account_id": connapse_id})
                if isinstance(matches, list):
                    self._connapse_cache = matches
                    self._connapse_cache_time = now
                else:
                    matches = self._connapse_cache or []

            if not matches:
                return "⚠️ Chưa tìm thấy lịch sử đấu chung với tri kỷ connapse trên OpenDota!"

            with_games = 0
            with_win = 0
            streamer_kills = 0
            streamer_deaths = 0
            streamer_assists = 0
            total_sec = 0
            connapse_heroes: Dict[int, int] = {}

            for m in matches:
                my_slot = m.get("player_slot", 0)
                my_radiant = my_slot < 128
                radiant_win = m.get("radiant_win", False)
                my_win = (radiant_win and my_radiant) or (not radiant_win and not my_radiant)

                heroes_map = m.get("heroes") or {}
                connapse_slot = None
                connapse_hero = None
                for slot_str, p_info in heroes_map.items():
                    if str(p_info.get("account_id")) == connapse_id:
                        connapse_slot = int(slot_str)
                        connapse_hero = p_info.get("hero_id")
                        break

                is_same_team = (connapse_slot is not None) and ((my_slot < 128) == (connapse_slot < 128))
                if is_same_team:
                    with_games += 1
                    if my_win:
                        with_win += 1
                    total_sec += m.get("duration", 0)
                    streamer_kills += m.get("kills", 0)
                    streamer_deaths += m.get("deaths", 0)
                    streamer_assists += m.get("assists", 0)
                    if connapse_hero:
                        connapse_heroes[connapse_hero] = connapse_heroes.get(connapse_hero, 0) + 1

            if with_games == 0:
                return "⚠️ Chưa tìm thấy trận đấu chung team nào giữa streamer và connapse!"

            hours = total_sec // 3600
            minutes = (total_sec % 3600) // 60
            wr = (with_win / max(1, with_games)) * 100.0
            kp_avg = (streamer_kills + streamer_assists) / max(1, with_games)

            top_h = sorted(connapse_heroes.items(), key=lambda x: x[1], reverse=True)[:4]
            top_h_str = ", ".join([f"{self.get_hero_short_name(h_id)} {cnt} trận" for h_id, cnt in top_h])

            max_dur = max(m.get("duration", 0) for m in matches) // 60
            min_dur = min(m.get("duration", 0) for m in matches) // 60

            latest_ts = matches[0].get("start_time", 0)
            latest_date = datetime.fromtimestamp(latest_ts, tz=self.tz).strftime("%d/%m")

            facts = [
                f"🤝 Tri kỷ connapse: {with_games} trận kề vai sát cánh ({hours}h{minutes:02d}p), 100% CÙNG PHE chưa từng đối đầu! Kết quả: {with_win}W - {with_games - with_win}L ({wr:.1f}%).",
                f"🌸 connapse - Em gái quốc dân: Chuyên pick Support bảo kê ({top_h_str}) để streamer tha hồ múa lửa gánh team!",
                f"🔥 Cặp đôi huỷ diệt: Trong {with_games} trận duo với connapse, streamer bỏ túi {streamer_kills} Kills & {streamer_assists} Assists (trung bình {kp_avg:.1f} mạng đóng góp/trận)!",
                f"⏱️ Kỷ lục duo cùng connapse: Trận lầy lội nhất kéo dài {max_dur} phút kịch chiến, còn trận ngắn nhất kết thúc chóng vánh chỉ sau đúng {min_dur} phút!",
                f"🍻 Tình đồng chí keo sơn: Cùng cày {hours}h{minutes:02d}p Dota 2, trận gần nhất vừa quẩy ngày {latest_date}! Dù winrate {wr:.1f}% nhưng tình cảm đồng đội không bao giờ rạn nứt."
            ]

            chosen_idx = self._draw_from_deck(self._connapse_deck, len(facts))
            return facts[chosen_idx]
        except Exception as e:
            logger.error(f"Lỗi trong get_connapse_message: {e}", exc_info=True)
            return "⚠️ Máy chủ OpenDota đang phản hồi chậm, bạn vui lòng thử lại sau vài giây!"

    def get_tworax_message(self) -> str:
        """Easter egg cho lệnh !2rax: Giai thoại kinh điển 2 rax TNC tại vòng loại TI8."""
        events = [
            "🏰 2 Rax TNC (TI8 Qualifiers): Phút 40, TNC Tigers dẫn hơn 20.000 net worth, 458 đập tan 2 cửa rax của TNC Predator! Giấc mơ The International lần đầu cho VN chỉ còn cách đúng 1 combat định mệnh.",
            "🧜‍♂️ Ác mộng Naga Siren: Pha phòng ngự điên rồ nhất lịch sử vòng loại TI khi Tims dùng Song of the Siren câu giờ từng đợt Mega Creeps, khiến giấc mơ đi Canada của 458 tan thành mây khói!",
            "📜 Châm ngôn kênh chat: 'Chừng nào nhà chính (Ancient) chưa nổ thì dẫn 2 rax như TNC vẫn thua!' Bài học xương máu đắt giá nhất sự nghiệp thi đấu chuyên nghiệp của streamer Trịnh 458.",
            "🤝 Duyên nợ bất tận: inYourdreaM (IYD) năm xưa cùng 458 khóc hận vụ 2 rax, nay đã gặp lại nhau 89 trận ở pub SEA! Còn đối thủ lật kèo năm ấy là Kuku cũng đã đụng độ streamer tới 123 trận.",
            "🇨🇦 Cách Vancouver một bước chân: Vụ 2 rax TNC 2018 là khoảnh khắc một tuyển thủ Dota 2 Việt Nam (458) ở gần sân khấu The International danh giá nhất thế giới hơn bất kỳ ai trong lịch sử!",
            "✈️ Vé đi Canada bị huỷ: 1437 và 458 đã chuẩn bị vali sang Vancouver dự TI8 với khoản tiền thưởng hàng chục triệu USD, cho đến khi TNC Predator tạo nên cú Mega Comeback thế kỷ xé toang tấm vé!",
            "💔 Vết thương không bao giờ lành: Trận thua 2 rax trước TNC Predator năm 2018 khiến 458 chia tay TNC Tigers về nước. Từ đó sinh ra 'hội chứng sợ quăng game' khi dẫn sâu của streamer!"
        ]
        chosen_idx = self._draw_from_deck(self._tworax_deck, len(events))
        return events[chosen_idx]

    def get_pro_message(self, query: Optional[str] = None) -> str:
        """Generate response for !pro <tên>: thống kê tỉ lệ đối đầu với pro player cụ thể."""
        try:
            pros = self.get_player_pros()
            if not pros:
                return "⚠️ Hiện chưa tải được danh sách Pro Player từ OpenDota, vui lòng thử lại sau!"

            def _clean(s: str) -> str:
                return re.sub(r"[^a-z0-9]", "", (s or "").lower())

            # Bảng tên hiển thị đẹp cho các pro có tên ký tự chữ Hán hoặc biệt danh đặc biệt
            custom_display_names = {
                158847773: "Tianming (天命)",
                137193239: "Paparazi (Eurus / 无限)",
                183378746: "Fantasy (Siamese.C / 皮球)",
                903184860: "Xiangyu (项羽)",
                118134220: "Bach (Faith_bian)",
                111114687: "y` (Innocence)",
                207829314: "BoBoKa (Borax)",
                324045303: "Chu Sheng (出省)",
                446737104: "Dong (冬 / Winter)",
                156662698: "Ava (阿发)",
                137515340: "Roujiamo (肉夹馍)",
                411596849: "Yu Wang (鱼王)",
                110142194: "Wu Ming (无名)",
                435460860: "Gen (根)",
                118842533: "Zhi Fei (知非)",
                212011074: "Zhang Zezhong (谢乐)",
                139223191: "Happy Noodles (快乐面条)",
                1511688542: "Meng Xin (萌新)",
                1095157609: "Nuan Xin (暖心)",
                86785208: "Super (Yakult)",
                # Các tuyển thủ quốc tế nổi tiếng
                70388657: "Dendi (B8)",
                94054712: "Topson (Tundra / OG)",
                86698277: "33 (Tundra / Liquid)",
                302214028: "Collapse (Team Spirit)",
                25907144: "Cr1t- (Falcons)",
                317880638: "Save- (BetBoom)",
                480412663: "gpk~ (BetBoom)",
                106305042: "Larl (Team Spirit)",
                201358612: "Nisha (Team Liquid)",
                898455820: "Malr1ne (Falcons)",
                132851371: "RAMZES666 (Tundra)",
                93618577: "bzm (OG)",
                97590558: "Ace (Gaimin Gladiators)",
                10366616: "Sneyking (Falcons)",
                116585378: "MidOne (MOUZ)",
                136829091: "Whitemon (Tundra)",
                375507918: "23savage (OG)",
                100594231: "skem (Shopify)",
                324277900: "Yopaj- (Shopify)",
                152545459: "Gabbi (Blacklist)",
                301750126: "Mikoto (Aurora)",
                132309493: "Raven (Blacklist)",
                155494381: "TIMS (Blacklist)",
                164532005: "Armel (Aurora)",
                206642367: "Ghost (Nigma)",
                113435203: "ChYuaN (Talon)",
                184138153: "Masaros (Bleed)",
                389022189: "Palos (Aurora)",
                173978074: "NothingToSay (Invictus)",
                76904792: "poloson (Bleed)",
                219755398: "Jîng (Nemesis)",
                392565237: "JACKBOYS (Nemesis)",
                181716137: "inYourdreaM (IYD)",
                184950344: "Kuku (Talon)",
            }

            if not query or not query.strip():
                top_pros = sorted(pros, key=lambda x: x.get("games", 0), reverse=True)[:4]
                items = [f"{custom_display_names.get(p.get('account_id'), p.get('name'))} ({p.get('games')} trận)" for p in top_pros if p.get("name")]
                return (
                    f"🏆 Top Pro hay gặp: hunghung (742 trận), {', '.join(items)}... "
                    "Gõ '!pro <tên>' (vd: !pro hunghung, !pro 23savage, !pro paparazi, !pro tianming) để xem tỉ lệ đối đầu!"
                )

            q_raw = query.strip().lower()
            q_clean = _clean(q_raw)

            # 1. Nhóm Pro đặc biệt không còn trong OpenDota /pros (bị ban / giải nghệ / cựu huyền thoại)
            CUSTOM_EXTRA_PROS = {
                # hunghung / bmk / htz (Banned by Valve in March 2022)
                "hunghung": (372105535, "hunghung (Htz / bmk)", "Ex-Apex"),
                "hung": (372105535, "hunghung (Htz / bmk)", "Ex-Apex"),
                "bmk": (372105535, "hunghung (Htz / bmk)", "Ex-Apex"),
                "htz": (372105535, "hunghung (Htz / bmk)", "Ex-Apex"),
                # Ana & Mushi
                "ana": (311360822, "Ana", "OG"),
                "mushi": (89871557, "Mushi", "Fnatic"),
                # Sccc
                "sccc": (149486894, "Sccc (S-God)", "Newbee"),
                "sgod": (149486894, "Sccc (S-God)", "Newbee"),
                # Somnus / Maybe
                "somnus": (106863163, "Somnus (Maybe)", "AR"),
                "maybe": (106863163, "Somnus (Maybe)", "AR"),
                # Chalice
                "chalice": (94738847, "Chalice", "AR"),
                # Ame
                "ame": (125581247, "Ame", "XG"),
            }

            if q_clean in CUSTOM_EXTRA_PROS:
                aid, display_name, team_tag = CUSTOM_EXTRA_PROS[q_clean]
                stats = self.get_custom_pro_stats(aid)
                if stats and stats.get("games", 0) > 0:
                    tot_g = stats["games"]
                    w_g = stats["with_games"]
                    w_w = stats["with_win"]
                    w_wr = (w_w / w_g * 100.0) if w_g else 0.0
                    a_g = stats["against_games"]
                    a_w = stats["against_win"]
                    a_wr = (a_w / a_g * 100.0) if a_g else 0.0
                    tag_str = f" ({team_tag})" if team_tag else ""
                    return (
                        f"⚔️ Streamer vs {display_name}{tag_str} (tổng {tot_g} trận): "
                        f"Chung team {w_g} trận ({w_w}W-{w_g - w_w}L, {w_wr:.1f}%) | "
                        f"Đối đầu {a_g} trận ({a_w}W-{a_g - a_w}L, {a_wr:.1f}%)"
                    )

            # 2. Giải thích chi tiết cho các siêu sao phương Tây / Bắc Mỹ mà streamer chưa từng gặp do dùng acc phụ / ẩn API khi sang SEA
            UNMET_PRO_EXPLANATIONS = {
                # Arteezy
                "rtz": "⚠️ Arteezy (RTZ) chủ yếu đánh cụm Bắc Mỹ (NA). Khi sang SEA bootcamp, RTZ thường dùng acc phụ ẩn dữ liệu nên API không lưu lịch sử công khai.",
                "arteezy": "⚠️ Arteezy (RTZ) chủ yếu đánh cụm Bắc Mỹ (NA). Khi sang SEA bootcamp, RTZ thường dùng acc phụ ẩn dữ liệu nên API không lưu lịch sử công khai.",
                "artour": "⚠️ Arteezy (RTZ) chủ yếu đánh cụm Bắc Mỹ (NA). Khi sang SEA bootcamp, RTZ thường dùng acc phụ ẩn dữ liệu nên API không lưu lịch sử công khai.",
                # Miracle-
                "miracle": "⚠️ Miracle- chủ yếu đánh cụm EU/MENA. Khi sang SEA bootcamp/đánh giải, anh thường dùng acc phụ hoặc ẩn dữ liệu nên API không lưu lịch sử công khai.",
                "miracle-": "⚠️ Miracle- chủ yếu đánh cụm EU/MENA. Khi sang SEA bootcamp/đánh giải, anh thường dùng acc phụ hoặc ẩn dữ liệu nên API không lưu lịch sử công khai.",
                # SumaiL
                "sumail": "⚠️ SumaiL (The King) chủ yếu đánh cụm NA/EU. Khi sang SEA bootcamp, anh thường dùng acc phụ hoặc ẩn dữ liệu nên API không lưu lịch sử công khai.",
                "king": "⚠️ SumaiL (The King) chủ yếu đánh cụm NA/EU. Khi sang SEA bootcamp, anh thường dùng acc phụ hoặc ẩn dữ liệu nên API không lưu lịch sử công khai.",
                # Yatoro / Raddan
                "yatoro": "⚠️ Yatoro (Raddan) chủ yếu đánh cụm Đông Âu. Khi sang SEA bootcamp/đánh giải, anh thường dùng acc phụ hoặc ẩn dữ liệu nên API không lưu lịch sử công khai.",
                "raddan": "⚠️ Yatoro (Raddan) chủ yếu đánh cụm Đông Âu. Khi sang SEA bootcamp/đánh giải, anh thường dùng acc phụ hoặc ẩn dữ liệu nên API không lưu lịch sử công khai.",
                # Satanic
                "satanic": "⚠️ Satanic chủ yếu đánh cụm Đông Âu/EU. Khi sang SEA bootcamp, tuyển thủ thường dùng acc phụ hoặc ẩn dữ liệu nên API không lưu lịch sử công khai.",
                # ATF / Ammar
                "atf": "⚠️ ATF (Ammar) chủ yếu đánh cụm EU/MENA. Khi sang SEA bootcamp/đánh giải, anh thường dùng acc phụ hoặc ẩn dữ liệu nên API không lưu lịch sử công khai.",
                "ammar": "⚠️ ATF (Ammar) chủ yếu đánh cụm EU/MENA. Khi sang SEA bootcamp/đánh giải, anh thường dùng acc phụ hoặc ẩn dữ liệu nên API không lưu lịch sử công khai.",
                # Quinn / CCnC
                "quinn": "⚠️ Quinn (CCnC) chủ yếu đánh cụm EU/NA. Khi sang SEA bootcamp/đánh giải, anh thường dùng acc phụ hoặc ẩn dữ liệu nên API không lưu lịch sử công khai.",
                "ccnc": "⚠️ Quinn (CCnC) chủ yếu đánh cụm EU/NA. Khi sang SEA bootcamp/đánh giải, anh thường dùng acc phụ hoặc ẩn dữ liệu nên API không lưu lịch sử công khai.",
                # Pure
                "pure": "⚠️ Pure~ chủ yếu đánh cụm Đông Âu/EU. Khi sang SEA bootcamp/đánh giải, anh thường dùng acc phụ hoặc ẩn dữ liệu nên API không lưu lịch sử công khai.",
                # TORONTOTOKYO
                "torontotokyo": "⚠️ TORONTOTOKYO chủ yếu đánh cụm Đông Âu. Khi sang SEA bootcamp, tuyển thủ thường dùng acc phụ hoặc ẩn dữ liệu nên API không lưu lịch sử công khai.",
                # Nightfall
                "nightfall": "⚠️ Nightfall chủ yếu đánh cụm Đông Âu. Khi sang SEA bootcamp, tuyển thủ thường dùng acc phụ hoặc ẩn dữ liệu nên API không lưu lịch sử công khai.",
                # Skiter
                "skiter": "⚠️ Skiter chủ yếu đánh cụm Châu Âu. Khi sang SEA bootcamp/đánh giải, anh thường dùng acc phụ hoặc ẩn dữ liệu nên API không lưu lịch sử công khai.",
                # Ceb & N0tail
                "ceb": "⚠️ Ceb chủ yếu đánh cụm Tây Âu. Khi sang SEA bootcamp/đánh giải, anh thường dùng acc phụ hoặc ẩn dữ liệu nên API không lưu lịch sử công khai.",
                "notail": "⚠️ N0tail chủ yếu đánh cụm Tây Âu. Khi sang SEA bootcamp/đánh giải, anh thường dùng acc phụ hoặc ẩn dữ liệu nên API không lưu lịch sử công khai.",
                "n0tail": "⚠️ N0tail chủ yếu đánh cụm Tây Âu. Khi sang SEA bootcamp/đánh giải, anh thường dùng acc phụ hoặc ẩn dữ liệu nên API không lưu lịch sử công khai.",
                # Puppey & KuroKy
                "puppey": "⚠️ Puppey chủ yếu đánh cụm Châu Âu. Khi sang SEA bootcamp/đánh giải, anh thường dùng acc phụ hoặc ẩn dữ liệu nên API không lưu lịch sử công khai.",
                "kuroky": "⚠️ KuroKy chủ yếu đánh cụm Châu Âu. Khi sang SEA bootcamp/đánh giải, anh thường dùng acc phụ hoặc ẩn dữ liệu nên API không lưu lịch sử công khai.",
                "kuro": "⚠️ KuroKy chủ yếu đánh cụm Châu Âu. Khi sang SEA bootcamp/đánh giải, anh thường dùng acc phụ hoặc ẩn dữ liệu nên API không lưu lịch sử công khai.",
            }

            if q_clean in UNMET_PRO_EXPLANATIONS:
                return UNMET_PRO_EXPLANATIONS[q_clean]

            # 2. Ánh xạ alias trực tiếp sang account_id cho các Pro Trung Quốc / có ký tự chữ Hán / ký tự lạ
            PRO_ACCOUNT_MAP = {
                # Paparazi / Eurus
                "paparazi": 137193239,
                "paparazzi": 137193239,
                "eurus": 137193239,
                "paparazi灬": 137193239,
                "无限": 137193239,
                # Tianming
                "tianming": 158847773,
                "tian ming": 158847773,
                "thienmenh": 158847773,
                "thien menh": 158847773,
                "thiên mệnh": 158847773,
                "天命": 158847773,
                # Fantasy / Siamese.C / Piqiu
                "piqiu": 183378746,
                "pi qiu": 183378746,
                "fantasy": 183378746,
                "siamese.c": 183378746,
                "siamesec": 183378746,
                "皮球": 183378746,
                # Xiangyu
                "xiangyu": 903184860,
                "xiang yu": 903184860,
                "hangvu": 903184860,
                "hang vu": 903184860,
                "hạng vũ": 903184860,
                "项羽": 903184860,
                # Bach / Faith_bian
                "bach": 118134220,
                "faith_bian": 118134220,
                "faithbian": 118134220,
                "faith bian": 118134220,
                # y` / Innocence
                "y`": 111114687,
                "y'": 111114687,
                "innocence": 111114687,
                "ygod": 111114687,
                "y-god": 111114687,
                # BoBoKa / Borax
                "boboka": 207829314,
                "borax": 207829314,
                # Chu Sheng
                "chusheng": 324045303,
                "chu sheng": 324045303,
                "xuattinh": 324045303,
                "xuất tỉnh": 324045303,
                "出省": 324045303,
                # Dong / Winter
                "dong": 446737104,
                "winter": 446737104,
                "gedongdong": 446737104,
                "冬": 446737104,
                # Ava / Afa
                "ava": 156662698,
                "afa": 156662698,
                "avaafa": 156662698,
                "阿发": 156662698,
                # Roujiamo
                "roujiamo": 137515340,
                "thitkep": 137515340,
                "thịt kẹp": 137515340,
                "肉夹馍": 137515340,
                # Yu Wang
                "yuwang": 411596849,
                "yu wang": 411596849,
                "kingoffish": 411596849,
                "nguvuong": 411596849,
                "ngư vương": 411596849,
                "鱼王": 411596849,
                # Wu Ming
                "wuming": 110142194,
                "wu ming": 110142194,
                "vodanh": 110142194,
                "vô danh": 110142194,
                "无名": 110142194,
                # Gen
                "gen": 435460860,
                "根": 435460860,
                # Zhi Fei
                "zhifei": 118842533,
                "zhi fei": 118842533,
                "知非": 118842533,
                # Zhang Zezhong / Xie Le
                "xiele": 212011074,
                "xie le": 212011074,
                "zhangzezhong": 212011074,
                "谢乐": 212011074,
                # Happy Noodles
                "happynoodles": 139223191,
                "kuailemientiao": 139223191,
                "mivuive": 139223191,
                "mì vui vẻ": 139223191,
                "快乐面条": 139223191,
                # Meng Xin
                "mengxin": 1511688542,
                "meng xin": 1511688542,
                "萌新": 1511688542,
                # Nuan Xin
                "nuanxin": 1095157609,
                "nuan xin": 1095157609,
                "暖心": 1095157609,
                # Tuyển thủ phương Tây & SEA nổi bật
                "topson": 94054712,
                "topgod": 94054712,
                "godson": 94054712,
                "dendi": 70388657,
                "anhba": 70388657,
                "anh ba": 70388657,
                "33": 86698277,
                "net33": 86698277,
                "collapse": 302214028,
                "cr1t": 25907144,
                "crit": 25907144,
                "save": 317880638,
                "gpk": 480412663,
                "larl": 106305042,
                "nisha": 201358612,
                "malr1ne": 898455820,
                "malrine": 898455820,
                "bzm": 93618577,
                "ramzes": 132851371,
                "ramzes666": 132851371,
                "ace": 97590558,
                "sneyking": 10366616,
                "midone": 116585378,
                "whitemon": 136829091,
                "23": 375507918,
                "23savage": 375507918,
                "skem": 100594231,
                "yopaj": 324277900,
                "gabbi": 152545459,
                "mikoto": 301750126,
                "raven": 132309493,
                "tims": 155494381,
                "armel": 164532005,
                "ghost": 206642367,
                "jackboys": 392565237,
                "jackboy": 392565237,
                "jing": 219755398,
                "chyuan": 113435203,
                "masaros": 184138153,
                "palos": 389022189,
                "nts": 173978074,
                "nothingtosay": 173978074,
                "poloson": 76904792,
                "inyourdream": 181716137,
                "iyd": 181716137,
                "kuku": 184950344,
            }

            matched = None
            if q_raw in PRO_ACCOUNT_MAP:
                target_acc_id = PRO_ACCOUNT_MAP[q_raw]
                for p in pros:
                    if p.get("account_id") == target_acc_id:
                        matched = p
                        break

            if not matched and q_clean in PRO_ACCOUNT_MAP:
                target_acc_id = PRO_ACCOUNT_MAP[q_clean]
                for p in pros:
                    if p.get("account_id") == target_acc_id:
                        matched = p
                        break

            # 3. Biệt danh (aliases) chuẩn sang tên pro player
            PRO_ALIASES = {
                "crit": "cr1t",
                "malrine": "malr1ne",
                "marl1ne": "malr1ne",
                "23": "23savage",
                "nts": "nothingtosay",
                "ana": "ananas$s",
                "super": "yakult",
                "iyd": "inyourdream",
            }

            if not matched:
                q_target = PRO_ALIASES.get(q_clean, q_clean)

                if q_target:
                    # 1. Khớp chính xác tên chuẩn
                    for p in pros:
                        if _clean(p.get("name")) == q_target:
                            matched = p
                            break

                    # 2. Khớp bắt đầu bằng (prefix)
                    if not matched:
                        for p in pros:
                            if _clean(p.get("name")).startswith(q_target):
                                matched = p
                                break

                    # 3. Khớp chuỗi con trong tên
                    if not matched:
                        for p in pros:
                            if q_target in _clean(p.get("name")):
                                matched = p
                                break

                    # 4. Khớp trong Steam personaname
                    if not matched:
                        for p in pros:
                            if q_target in _clean(p.get("personaname")):
                                matched = p
                                break

            if not matched:
                return f"⚠️ Không tìm thấy lịch sử đấu với '{query.strip()}'. Tuyển thủ có thể dùng acc phụ hoặc tắt chia sẻ dữ liệu (ẩn API) nên không lưu công khai."

            has_custom = matched.get("account_id") in custom_display_names
            p_name = custom_display_names.get(matched.get("account_id")) or matched.get("name") or matched.get("personaname")
            tag = f" ({matched['team_tag']})" if (matched.get("team_tag") and not has_custom) else ""
            tot_g = matched.get("games", 0)
            w_g = matched.get("with_games", 0)
            w_w = matched.get("with_win", 0)
            w_wr = (w_w / w_g * 100.0) if w_g else 0.0
            a_g = matched.get("against_games", 0)
            a_w = matched.get("against_win", 0)
            a_wr = (a_w / a_g * 100.0) if a_g else 0.0

            return (
                f"⚔️ Streamer vs {p_name}{tag} (tổng {tot_g} trận): "
                f"Chung team {w_g} trận ({w_w}W-{w_g - w_w}L, {w_wr:.1f}%) | "
                f"Đối đầu {a_g} trận ({a_w}W-{a_g - a_w}L, {a_wr:.1f}%)"
            )
        except Exception as e:
            logger.error(f"Lỗi trong get_pro_message: {e}", exc_info=True)
            return "⚠️ Máy chủ OpenDota đang phản hồi chậm, bạn vui lòng thử lại sau vài giây!"

    def _load_dieback_cache(self) -> Dict[str, Any]:
        """Tải dữ liệu cache dieback từ file json local."""
        if os.path.exists(self.dieback_cache_file):
            try:
                with open(self.dieback_cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Lỗi đọc dieback cache: {e}")
        return {}

    def _save_dieback_cache(self):
        """Lưu dữ liệu cache dieback vào file json local."""
        try:
            with open(self.dieback_cache_file, "w", encoding="utf-8") as f:
                json.dump(self._dieback_cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Lỗi lưu dieback cache: {e}")

    def get_match_dieback_info(self, match_id: Union[int, str], m_meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Lấy thông tin dieback cho một trận đấu, ưu tiên từ cache, nếu chưa có thì fetch và lưu cache."""
        mid = str(match_id)
        if mid in self._dieback_cache:
            return self._dieback_cache[mid]

        # Nếu metadata cho thấy trận chưa parse hoặc 0 deaths thì lưu luôn không có dieback
        if m_meta:
            if m_meta.get("version") is None or m_meta.get("deaths", 0) == 0:
                entry = {
                    "parsed": bool(m_meta.get("version")),
                    "hero_id": m_meta.get("hero_id"),
                    "win": self._is_win(m_meta),
                    "diebacks": []
                }
                self._dieback_cache[mid] = entry
                return entry

        try:
            mdata = self._api_get(f"/matches/{mid}")
            if not mdata or "players" not in mdata:
                entry = {"parsed": False, "diebacks": []}
                self._dieback_cache[mid] = entry
                return entry

            p = next((x for x in mdata["players"] if str(x.get("account_id")) == self.account_id), None)
            if not p:
                entry = {"parsed": False, "diebacks": []}
                self._dieback_cache[mid] = entry
                return entry

            bb_log = p.get("buyback_log") or []
            deaths_log = p.get("deaths_log") or []
            diebacks = []
            for bb in bb_log:
                b_t = bb.get("time", 0)
                next_deaths = [d for d in deaths_log if d.get("time", 0) > b_t]
                if next_deaths:
                    nd = next_deaths[0]
                    dt = nd.get("time", 0) - b_t
                    if dt <= 120:  # Chết lại trong vòng 2 phút sau khi buyback
                        killer_raw = nd.get("key", "").replace("npc_dota_hero_", "").replace("dota_", "")
                        diebacks.append({
                            "bb_time": b_t,
                            "death_time": nd.get("time", 0),
                            "sec_after_bb": dt,
                            "killer": killer_raw
                        })
            entry = {
                "parsed": True,
                "hero_id": p.get("hero_id"),
                "win": p.get("win") == 1,
                "diebacks": diebacks
            }
            self._dieback_cache[mid] = entry
            self._save_dieback_cache()
            return entry
        except Exception as e:
            logger.error(f"Lỗi kiểm tra dieback cho trận {mid}: {e}")
            return {"parsed": False, "diebacks": []}

    def get_dieback_message(self, query: Optional[str] = None) -> str:
        """Thống kê dieback của streamer trong ca stream hiện tại hoặc 100 trận gần nhất."""
        try:
            q = (query or "").strip().lower()

            def _fmt_killer(k_str: Optional[str]) -> str:
                if not k_str:
                    return "Đối thủ"
                clean = k_str.replace("npc_dota_hero_", "").replace("dota_", "").replace("_", " ").title()
                return HERO_ABBREVIATIONS.get(clean, clean)

            # 1. Thống kê tổng hợp 100 trận nếu người dùng gõ: !dieback 100, !dieback all, !dieback top
            if q in ["100", "all", "top", "max"]:
                all_diebacks = []
                hero_counts = Counter()
                fastest = (999, None, None, None)
                for mid, d in self._dieback_cache.items():
                    for db in d.get("diebacks", []):
                        hid = d.get("hero_id")
                        all_diebacks.append((mid, hid, db, d.get("win")))
                        if hid:
                            hero_counts[hid] += 1
                        sec = db.get("sec_after_bb", 999)
                        if sec < fastest[0]:
                            fastest = (sec, hid, db.get("killer"), mid)

                top_str = ""
                if hero_counts:
                    top_h = hero_counts.most_common(2)
                    top_str = f" Hay nướng tiền nhất: {', '.join([f'{self.get_hero_short_name(h)} ({c} lần)' for h, c in top_h])}."

                fastest_str = ""
                if fastest[1] is not None:
                    h_name = self.get_hero_short_name(fastest[1])
                    k_name = _fmt_killer(fastest[2])
                    fastest_str = f" Kỷ lục ngã ngửa: {h_name} BB xong nằm xuống sau đúng {fastest[0]}s bởi {k_name}!"

                return f"💀 Thống kê 100 trận gần nhất: {len(all_diebacks)} pha Dieback!{top_str}{fastest_str}"

            # 2. Mặc định: Thống kê trong ca stream hôm nay (session)
            session_matches = self.get_session_matches()
            if not session_matches:
                tot_100 = sum(len(d.get("diebacks", [])) for d in self._dieback_cache.values())
                return f"📅 Ca stream hôm nay chưa có trận nào. Tổng 100 trận gần nhất có {tot_100} pha Dieback! Kỷ lục: Storm Spirit vừa BB xong đếm số sau 6s bởi Huskar."

            session_diebacks = []
            for m in session_matches:
                mid = m.get("match_id")
                info = self.get_match_dieback_info(mid, m_meta=m)
                for db in info.get("diebacks", []):
                    session_diebacks.append({
                        "match_id": mid,
                        "hero_id": m.get("hero_id"),
                        "win": self._is_win(m),
                        "bb_time": db.get("bb_time", 0),
                        "death_time": db.get("death_time", 0),
                        "sec": db.get("sec_after_bb", 0),
                        "killer": db.get("killer", "")
                    })

            n_matches = len(session_matches)
            if not session_diebacks:
                tot_100 = sum(len(d.get("diebacks", [])) for d in self._dieback_cache.values())
                return (
                    f"🎉 Ca stream hôm nay ({n_matches} trận): 0 pha Dieback, streamer đánh rất tỉnh táo! "
                    f"(100 trận gần nhất có {tot_100} pha, kỷ lục: Storm Spirit BB xong hẹo sau đúng 6s bởi Huskar)."
                )

            # Có dieback trong ca hôm nay
            db_count = len(session_diebacks)
            latest = session_diebacks[0]
            h_name = self.get_hero_short_name(latest["hero_id"])
            b_min = latest["bb_time"] // 60
            b_sec = latest["bb_time"] % 60
            k_name = _fmt_killer(latest["killer"])
            res = "Thắng" if latest["win"] else "Thua"

            return (
                f"💀 Ca stream hôm nay ({n_matches} trận): Streamer có {db_count} pha Dieback! "
                f"Trận {h_name} (BB phút {b_min}:{b_sec:02d} -> bay màu sau {latest['sec']}s bởi {k_name}). Kết quả: {res}."
            )
        except Exception as e:
            logger.error(f"Lỗi trong get_dieback_message: {e}", exc_info=True)
            return "⚠️ Máy chủ OpenDota đang phản hồi chậm, bạn vui lòng thử lại sau vài giây!"



