import math
import time
import re
import random
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
import threading
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
        self._connapse_cache: Optional[List[Dict[str, Any]]] = None
        self._connapse_cache_time = 0.0
        self.cache_ttl_connapse = 86400.0  # 24 hours
        self._last_connapse_idx: int = -1
        
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
            resp = self.session.get(url, params=params, timeout=8)
            if resp.status_code != 200:
                return []
            data = resp.json().get("result", {})
            raw_matches = data.get("matches", [])
            
            parsed_matches = []
            for rm in raw_matches:
                match_id = rm.get("match_id")
                start_time = rm.get("start_time")
                
                player_entry = next((p for p in rm.get("players", []) if str(p.get("account_id")) == self.account_id), None)
                if not player_entry:
                    continue
                
                hero_id = player_entry.get("hero_id")
                player_slot = player_entry.get("player_slot", 0)
                
                det_url = "https://api.steampowered.com/IDOTA2Match_570/GetMatchDetails/v1/"
                det_resp = self.session.get(det_url, params={"key": self.steam_api_key, "match_id": match_id}, timeout=6)
                if det_resp.status_code == 200:
                    d_data = det_resp.json().get("result", {})
                    radiant_win = d_data.get("radiant_win", False)
                    duration = d_data.get("duration", 0)
                    p_detail = next((p for p in d_data.get("players", []) if str(p.get("account_id")) == self.account_id), {})
                    kills = p_detail.get("kills", 0)
                    deaths = p_detail.get("deaths", 0)
                    assists = p_detail.get("assists", 0)
                else:
                    radiant_win = False
                    duration = 0
                    kills, deaths, assists = 0, 0, 0

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
        except Exception:
            return []

    def get_recent_matches(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Fetch recent matches: compares STRATZ, Steam Web API and OpenDota to pick the most up-to-date data."""
        now = time.time()
        if not force_refresh and self._matches_cache and (now - self._matches_cache_time < self.cache_ttl_matches):
            return self._matches_cache

        self.trigger_opendota_refresh()

        candidates: List[List[Dict[str, Any]]] = []

        # 1. Thử lấy từ STRATZ API
        stratz_matches = self._fetch_stratz_matches()
        if stratz_matches:
            candidates.append(stratz_matches)

        # 2. Thử lấy từ Steam Web API
        steam_matches = self._fetch_steam_matches()
        if steam_matches:
            candidates.append(steam_matches)

        # 3. Lấy từ OpenDota (kết hợp cả /recentMatches cập nhật nhanh và /matches)
        try:
            recent_m = self._api_get(f"players/{self.account_id}/recentMatches")
            if recent_m and isinstance(recent_m, list):
                candidates.append(recent_m)
        except Exception as e:
            logger.warning(f"Lỗi khi lấy recentMatches từ OpenDota: {e}")

        try:
            opendota_matches = self._api_get(f"players/{self.account_id}/matches", params={"limit": 25})
            if opendota_matches and isinstance(opendota_matches, list):
                candidates.append(opendota_matches)
        except Exception as e:
            logger.warning(f"Lỗi khi lấy từ OpenDota: {e}")

        # Chọn nguồn có trận đấu mới nhất (start_time hoặc match_id cao nhất)
        if candidates:
            best_source = max(candidates, key=lambda match_list: match_list[0].get("match_id", 0) if match_list else 0)
            self._matches_cache = best_source
            self._matches_cache_time = now
            return best_source

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

            base_msg = (
                f"🔥 Ca hôm nay ({now.strftime('%d/%m')}): {wins}W - {losses}L ({wr:.1f}%) | "
                f"Vừa xong: {lat_hero} ({lat_kda}) {lat_res} | Tướng: "
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
            tot_matches = int(totals.get("kills", {}).get("n", 1))
            matches_per_courier = round(tot_matches / max(1, couriers), 1)

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

            stuns_sec = int(totals.get("stuns", {}).get("sum", 0))
            stuns_hours = round(stuns_sec / 3600.0, 1)
            stuns_days = round(stuns_hours / 24.0, 1)

            towers = int(totals.get("tower_kills", {}).get("sum", 0))
            if towers >= 10000:
                tower_desc = "chính thức vượt mốc kỷ lục 10.000 công trình khiến thợ xây thất nghiệp!"
            else:
                tower_desc = f"chỉ còn {10000 - towers} trụ nữa là cán mốc 10.000 công trình!"

            tps = int(totals.get("purchase_tpscroll", {}).get("sum", 0))
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
                f"🎭 Fun fact: 💥 {name} đã farm {_fmt(total_creeps)} lính và quái rừng! Gây {dmg_mil} Triệu sát thương lên hero — bằng máu của 150.000 con Roshan.",
                f"🎭 Fun fact: ⏳ {name} đã stun đối thủ tổng cộng {_fmt(stuns_sec)} giây (~{stuns_hours} giờ)! Bắt đối phương đứng im bất động suốt {stuns_days} ngày liên tục.",
                f"🎭 Fun fact: 🏛️ {name} đích thị là máy xúc khi san phẳng {_fmt(towers)} trụ đối phương — {tower_desc}",
                f"🎭 Fun fact: 📜 {name} đã mua {_fmt(tps)} cuộn giấy TP Scroll (~3 triệu vàng tiền xe ôm) và tự tay chối bỏ (deny) {_fmt(denies)} lính đồng minh.",
                f"🎭 Fun fact: 👁️ {name} đã cắm {_fmt(total_wards)} cắm mắt ({_fmt(obs)} mắt xanh, {_fmt(sent)} mắt tím) — cắm đủ thắp sáng rực cả bản đồ!",
                f"🎭 Fun fact: ⏱️ {name} cống hiến {_fmt(hours)} giờ ({days} ngày đêm) cho Dota 2! Bỏ túi {_fmt(kills)} Kills, {_fmt(assists)} Assists với KDA trung bình {kda_avg:.2f}."
            ]

            available = [i for i in range(len(facts)) if i != self._last_funfact_idx]
            chosen_idx = random.choice(available) if available else 0
            self._last_funfact_idx = chosen_idx
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
                f"⏱️ Kỷ lục duo cùng connapse: Trận lầy lội nhất kéo dài {max_dur} phút căng thẳng, còn trận nhanh nhất ép đối thủ gõ GG chỉ sau đúng {min_dur} phút!",
                f"🍻 Tình đồng chí keo sơn: Cùng cày {hours}h{minutes:02d}p Dota 2, trận gần nhất vừa quẩy ngày {latest_date}! Dù winrate {wr:.1f}% nhưng tình anh em không bao giờ rạn nứt."
            ]

            available = [i for i in range(len(facts)) if i != self._last_connapse_idx]
            chosen_idx = random.choice(available) if available else 0
            self._last_connapse_idx = chosen_idx
            return facts[chosen_idx]
        except Exception as e:
            logger.error(f"Lỗi trong get_connapse_message: {e}", exc_info=True)
            return "⚠️ Máy chủ OpenDota đang phản hồi chậm, bạn vui lòng thử lại sau vài giây!"

    def get_pro_message(self, query: Optional[str] = None) -> str:
        """Generate response for !pro <tên>: thống kê tỉ lệ đối đầu với pro player cụ thể."""
        try:
            pros = self.get_player_pros()
            if not pros:
                return "⚠️ Hiện chưa tải được danh sách Pro Player từ OpenDota, vui lòng thử lại sau!"

            if not query or not query.strip():
                top_pros = sorted(pros, key=lambda x: x.get("games", 0), reverse=True)[:4]
                items = [f"{p.get('name')} ({p.get('games')} trận)" for p in top_pros if p.get("name")]
                return (
                    f"🏆 Top Pro hay gặp: {', '.join(items)}... "
                    "Gõ '!pro <tên>' (vd: !pro 23savage, !pro topson, !pro skem) để xem tỉ lệ đối đầu!"
                )

            q_raw = query.strip().lower()
            PRO_ALIASES = {
                "crit": "cr1t",
                "malrine": "malr1ne",
                "marl1ne": "malr1ne",
                "23": "23savage",
                "nts": "nothingtosay",
                "ana": "ananas$s"
            }
            q_target = PRO_ALIASES.get(q_raw, q_raw)

            def _clean(s: str) -> str:
                return re.sub(r"[^a-z0-9]", "", (s or "").lower())

            q_clean = _clean(q_target)
            matched = None

            # 1. Khớp chính xác tên chuẩn
            for p in pros:
                if _clean(p.get("name")) == q_clean:
                    matched = p
                    break

            # 2. Khớp bắt đầu bằng (prefix)
            if not matched:
                for p in pros:
                    if _clean(p.get("name")).startswith(q_clean):
                        matched = p
                        break

            # 3. Khớp chuỗi con trong tên
            if not matched:
                for p in pros:
                    if q_clean in _clean(p.get("name")):
                        matched = p
                        break

            # 4. Khớp trong Steam personaname
            if not matched:
                for p in pros:
                    if q_clean in _clean(p.get("personaname")):
                        matched = p
                        break

            if not matched:
                return f"⚠️ Streamer chưa từng thi đấu cùng hoặc đối đầu với pro player nào có tên khớp '{query.strip()}'."

            p_name = matched.get("name") or matched.get("personaname")
            tag = f" ({matched['team_tag']})" if matched.get("team_tag") else ""
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


