import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
import requests

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
    def __init__(self, account_id: str = "196931374", api_key: Optional[str] = None, tz_offset_hours: int = 7, manual_mmr: Optional[str] = None):
        self.account_id = str(account_id)
        self.api_key = api_key
        self.tz = timezone(timedelta(hours=tz_offset_hours))
        self.manual_mmr = manual_mmr
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Dota2StreamBot/1.0 (OpenDota Integration)"
        })
        
        # In-memory caches
        self._heroes_cache: Dict[int, str] = {}
        self._profile_cache: Optional[Dict[str, Any]] = None
        self._profile_cache_time = 0.0
        self._matches_cache: Optional[List[Dict[str, Any]]] = None
        self._matches_cache_time = 0.0
        self.cache_ttl_profile = 60.0  # 1 minute
        self.cache_ttl_matches = 30.0  # 30 seconds

    def _api_get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
        url = f"https://api.opendota.com/api/{endpoint.lstrip('/')}"
        p = params.copy() if params else {}
        if self.api_key:
            p["api_key"] = self.api_key
        resp = self.session.get(url, params=p, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def get_hero_name(self, hero_id: int) -> str:
        """Fetch and cache hero names from OpenDota constants."""
        if not self._heroes_cache:
            try:
                data = self._api_get("constants/heroes")
                for hid_str, hero_info in data.items():
                    self._heroes_cache[int(hid_str)] = hero_info.get("localized_name", f"Hero #{hid_str}")
            except Exception as e:
                return f"Hero #{hero_id}"
        return self._heroes_cache.get(hero_id, f"Hero #{hero_id}")

    def get_player_data(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Fetch general player info (name, rank_tier, leaderboard_rank, mmr_estimate)."""
        now = time.time()
        if not force_refresh and self._profile_cache and (now - self._profile_cache_time < self.cache_ttl_profile):
            return self._profile_cache

        data = self._api_get(f"players/{self.account_id}")
        self._profile_cache = data
        self._profile_cache_time = now
        return data

    def get_recent_matches(self, force_refresh: bool = False, days: int = 7) -> List[Dict[str, Any]]:
        """Fetch recent matches played by the user."""
        now = time.time()
        if not force_refresh and self._matches_cache and (now - self._matches_cache_time < self.cache_ttl_matches):
            return self._matches_cache

        data = self._api_get(f"players/{self.account_id}/matches", params={"date": days})
        self._matches_cache = data
        self._matches_cache_time = now
        return data

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
        except Exception as e:
            return f"⚠️ Không thể lấy thông tin Rank: {e}"

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
            
            # If manual MMR is configured by the streamer, show it
            if self.manual_mmr:
                parts.append(f"MMR thực tế: ~{self.manual_mmr}")
            elif mmr_est:
                parts.append(f"Ước tính OpenDota: ~{mmr_est} MMR")
            elif leaderboard_rank:
                parts.append(f"Bảng xếp hạng: Top #{leaderboard_rank}")
            else:
                parts.append("Valve hiện ẩn chỉ số MMR chính xác từ API")
            
            return " | ".join(parts)
        except Exception as e:
            return f"⚠️ Không thể lấy thông tin MMR: {e}"

    def get_today_message(self) -> str:
        """Generate response for !today command."""
        try:
            matches = self.get_recent_matches()
            player = self.get_player_data()
            name = player.get("profile", {}).get("personaname", "Streamer")

            now = datetime.now(self.tz)
            start_of_today = datetime(now.year, now.month, now.day, tzinfo=self.tz)
            start_ts = int(start_of_today.timestamp())

            today_matches = [m for m in matches if m.get("start_time", 0) >= start_ts]

            if not today_matches:
                # Find the most recent match for context
                if matches:
                    last_m = matches[0]
                    is_radiant = last_m["player_slot"] < 128
                    won = (last_m["radiant_win"] and is_radiant) or (not last_m["radiant_win"] and not is_radiant)
                    hero_name = self.get_hero_name(last_m["hero_id"])
                    res_text = "Thắng" if won else "Thua"
                    kda = f"{last_m['kills']}/{last_m['deaths']}/{last_m['assists']}"
                    return f"📅 Hôm nay {name} chưa đánh trận nào! Trận gần nhất: {hero_name} ({kda} - {res_text})."
                return f"📅 Hôm nay {name} chưa có trận đấu nào được ghi nhận trên Dota 2."

            wins = 0
            losses = 0
            hero_counts: Dict[str, Dict[str, int]] = {}

            for m in today_matches:
                is_radiant = m["player_slot"] < 128
                won = (m["radiant_win"] and is_radiant) or (not m["radiant_win"] and not is_radiant)
                if won:
                    wins += 1
                else:
                    losses += 1
                
                h_name = self.get_hero_name(m["hero_id"])
                if h_name not in hero_counts:
                    hero_counts[h_name] = {"w": 0, "l": 0}
                if won:
                    hero_counts[h_name]["w"] += 1
                else:
                    hero_counts[h_name]["l"] += 1

            total = wins + losses
            wr = (wins / total * 100) if total > 0 else 0

            # Format heroes played summary
            hero_summary = []
            for h_name, stats in list(hero_counts.items())[:4]:
                hero_summary.append(f"{h_name} ({stats['w']}W-{stats['l']}L)")
            hero_str = ", ".join(hero_summary)

            # Latest match result
            latest = today_matches[0]
            lat_radiant = latest["player_slot"] < 128
            lat_won = (latest["radiant_win"] and lat_radiant) or (not latest["radiant_win"] and not lat_radiant)
            lat_hero = self.get_hero_name(latest["hero_id"])
            lat_res = "Thắng ✅" if lat_won else "Thua ❌"
            lat_kda = f"{latest['kills']}/{latest['deaths']}/{latest['assists']}"

            return (
                f"🔥 Hôm nay ({now.strftime('%d/%m')}): {wins}W - {losses}L ({wr:.1f}%) | "
                f"Trận vừa xong: {lat_hero} ({lat_kda}) {lat_res} | "
                f"Tướng: {hero_str}"
            )
        except Exception as e:
            return f"⚠️ Không thể lấy thông tin hôm nay: {e}"

    def get_last_match_message(self) -> str:
        """Generate response for !lastmatch command."""
        try:
            matches = self.get_recent_matches()
            if not matches:
                return "⚠️ Không tìm thấy trận đấu nào gần đây."

            m = matches[0]
            match_id = m.get("match_id")
            is_radiant = m["player_slot"] < 128
            won = (m["radiant_win"] and is_radiant) or (not m["radiant_win"] and not is_radiant)
            hero_name = self.get_hero_name(m["hero_id"])
            kda = f"{m['kills']}/{m['deaths']}/{m['assists']}"
            res_str = "Chiến Thắng 🏆" if won else "Thất Bại 💀"
            duration_min = m.get("duration", 0) // 60

            return (
                f"⚔️ Trận gần nhất: {hero_name} | Kết quả: {res_str} | "
                f"KDA: {kda} | Thời lượng: {duration_min}p | "
                f"Dotabuff: https://www.dotabuff.com/matches/{match_id}"
            )
        except Exception as e:
            return f"⚠️ Không thể lấy chi tiết trận gần nhất: {e}"

    def get_profile_message(self) -> str:
        """Generate response for !dotabuff / !profile command."""
        return (
            f"🌐 Dotabuff: https://www.dotabuff.com/players/{self.account_id} | "
            f"OpenDota: https://www.opendota.com/players/{self.account_id}"
        )
