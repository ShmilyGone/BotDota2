import time
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

class OpenDotaClient:
    def __init__(
        self,
        account_id: str = "196931374",
        api_key: Optional[str] = None,
        steam_api_key: Optional[str] = None,
        tz_offset_hours: int = 7,
        manual_mmr: Optional[str] = None,
        session_gap_hours: float = 5.0
    ):
        self.account_id = str(account_id)
        self.api_key = api_key
        self.steam_api_key = steam_api_key
        self.tz = timezone(timedelta(hours=tz_offset_hours))
        self.manual_mmr = manual_mmr
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
        
        self._last_refresh_time = 0.0

    def trigger_opendota_refresh(self):
        """Asynchronously notify OpenDota to sync recent matches from Valve."""
        now = time.time()
        if now - self._last_refresh_time > 120.0:
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

    def get_player_data(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Fetch player profile, rank and MMR estimates with stale cache fallback."""
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
        """Fetch recent matches with stale cache fallback on network drops."""
        now = time.time()
        if not force_refresh and self._matches_cache and (now - self._matches_cache_time < self.cache_ttl_matches):
            return self._matches_cache

        self.trigger_opendota_refresh()

        # Try Steam API first for 0s latency
        steam_matches = self._fetch_steam_matches()
        if steam_matches:
            self._matches_cache = steam_matches
            self._matches_cache_time = now
            return steam_matches

        # Fallback to OpenDota
        try:
            data = self._api_get(f"players/{self.account_id}/matches", params={"limit": 25})
            self._matches_cache = data
            self._matches_cache_time = now
            return data
        except Exception as e:
            # If server dropped connection, return existing cache instead of crashing
            if self._matches_cache:
                logger.warning(f"Lỗi mạng OpenDota, dùng dữ liệu trận đấu đã lưu trước đó: {e}")
                return self._matches_cache
            raise e

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

    def get_rank_message(self) -> str:
        """Generate response for !rank command."""
        try:
            player = self.get_player_data()
            profile = player.get("profile", {})
            name = profile.get("personaname", f"Player {self.account_id}")
            rank_tier = player.get("rank_tier")
            leaderboard_rank = player.get("leaderboard_rank")
            
            rank_str = self.format_rank(rank_tier, leaderboard_rank)
            return f"🏅 Rank hiện tại của {name}: {rank_str}"
        except Exception:
            return "⚠️ Máy chủ OpenDota đang phản hồi chậm, bạn vui lòng thử lại sau vài giây!"

    def get_mmr_message(self) -> str:
        """Generate response for !mmr command."""
        try:
            player = self.get_player_data()
            profile = player.get("profile", {})
            name = profile.get("personaname", f"Player {self.account_id}")
            rank_tier = player.get("rank_tier")
            leaderboard_rank = player.get("leaderboard_rank")
            mmr_est = player.get("mmr_estimate", {}).get("estimate")

            rank_str = self.format_rank(rank_tier, leaderboard_rank)
            parts = [f"📊 {name} | Rank: {rank_str}"]
            
            if self.manual_mmr:
                parts.append(f"MMR thực tế: ~{self.manual_mmr}")
            elif mmr_est:
                parts.append(f"Ước tính OpenDota: ~{mmr_est} MMR")
            elif leaderboard_rank:
                parts.append(f"Bảng xếp hạng: Top #{leaderboard_rank}")
            else:
                parts.append("Valve hiện ẩn chỉ số MMR chính xác từ API")
            
            return " | ".join(parts)
        except Exception:
            return "⚠️ Máy chủ OpenDota đang phản hồi chậm, bạn vui lòng thử lại sau vài giây!"

    def get_today_message(self) -> str:
        """Generate response for !today command based on the current stream session."""
        try:
            session_matches = self.get_session_matches()
            player = self.get_player_data()
            name = player.get("profile", {}).get("personaname", "Streamer")
            now = datetime.now(self.tz)

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
                
                h_name = self.get_hero_name(m.get("hero_id", 0))
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
            lat_hero = self.get_hero_name(latest.get("hero_id", 0))
            lat_res = "Thắng ✅" if lat_won else "Thua ❌"
            lat_kda = f"{latest.get('kills', 0)}/{latest.get('deaths', 0)}/{latest.get('assists', 0)}"

            base_msg = (
                f"🔥 Ca hôm nay ({now.strftime('%d/%m')}): {wins}W - {losses}L ({wr:.1f}%) | "
                f"Vừa xong: {lat_hero} ({lat_kda}) {lat_res} | Tướng: "
            )

            # Dynamically include as many heroes as possible up to YouTube's 195-char limit
            hero_items = [f"{h} ({s['w']}W-{s['l']}L)" for h, s in hero_counts.items()]
            included_heroes = []
            for item in hero_items:
                test_str = ", ".join(included_heroes + [item])
                if len(base_msg + test_str) <= 195:
                    included_heroes.append(item)
                else:
                    rem = len(hero_items) - len(included_heroes)
                    if rem > 0:
                        included_heroes.append(f"+{rem} tướng")
                    break

            if not included_heroes:
                included_heroes = hero_items[:3]

            return base_msg + ", ".join(included_heroes)
        except Exception:
            return "⚠️ Máy chủ OpenDota đang phản hồi chậm, bạn vui lòng thử lại sau vài giây!"

    def get_last_match_message(self) -> str:
        """Generate response for !lastmatch command."""
        try:
            matches = self.get_recent_matches()
            if not matches:
                return "⚠️ Không tìm thấy trận đấu nào gần đây."

            m = matches[0]
            match_id = m.get("match_id")
            is_radiant = m.get("player_slot", 0) < 128
            won = (m.get("radiant_win") and is_radiant) or (not m.get("radiant_win") and not is_radiant)
            hero_name = self.get_hero_name(m.get("hero_id", 0))
            kda = f"{m.get('kills', 0)}/{m.get('deaths', 0)}/{m.get('assists', 0)}"
            res_str = "Chiến Thắng 🏆" if won else "Thất Bại 💀"
            duration_min = m.get("duration", 0) // 60

            return (
                f"⚔️ Trận gần nhất: {hero_name} | Kết quả: {res_str} | "
                f"KDA: {kda} | Thời lượng: {duration_min}p | "
                f"Dotabuff: https://www.dotabuff.com/matches/{match_id}"
            )
        except Exception:
            return "⚠️ Máy chủ OpenDota đang phản hồi chậm, bạn vui lòng thử lại sau vài giây!"

    def get_profile_message(self) -> str:
        """Generate response for !dotabuff / !profile command."""
        return (
            f"🌐 Dotabuff: https://www.dotabuff.com/players/{self.account_id} | "
            f"OpenDota: https://www.opendota.com/players/{self.account_id}"
        )
