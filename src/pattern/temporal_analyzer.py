"""
Temporal Analyzer — Time-series risk prediction for memecoin markets.

Analyzes time-of-day, day-of-week, and geographic patterns to predict
high-risk windows for rug pulls, bot attacks, and liquidity drains.

Temporal Windows Detected:
1. The Rug Hour (02:00-05:00 UTC) — 78% of rug pulls happen here
2. Sniper Window (0-5 min post-launch) — Bot dominance at 90%
3. FOMO Peak (18:00-22:00 UTC) — Social volume peak, overnight dump risk
4. Dead Zone (08:00-12:00 UTC) — Lowest global activity, high slippage
5. Weekend Trap (Fri 20:00 - Mon 08:00 UTC) — Lower moderation, more scams
6. Golden Hour (14:00-16:00 UTC) — Best liquidity, most organic volume

Scoring Rules (from README):
- Historical attack frequency 3×+ baseline = +40 risk score
- Liquidity thins >50% vs daytime = +25 risk score
- Geographic gap (all major regions offline) = +20 risk score
- Weekend period = +15 risk score
- Major holiday in US/EU/Asia = +10 risk score
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"
TEMPORAL_DB_FILE = DATA_DIR / "temporal_patterns.json"

# Scoring constants from README specification
SCORE_ATTACK_FREQUENCY_3X = 40
SCORE_LIQUIDITY_THIN_50PCT = 25
SCORE_GEOGRAPHIC_GAP = 20
SCORE_WEEKEND = 15
SCORE_HOLIDAY = 10

# Weekend day-of-week constants (Monday=0, Sunday=6)
WEEKEND_DAYS = {5, 6}  # Saturday=5, Sunday=6


@dataclass
class TemporalRiskResult:
    """Comprehensive result of temporal risk analysis."""

    current_utc_time: str = ""
    risk_score: float = 0.0                    # 0-100
    active_windows: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    is_rug_hour: bool = False
    is_fomo_peak: bool = False
    is_dead_zone: bool = False
    is_weekend_trap: bool = False
    is_golden_hour: bool = False
    attack_frequency_multiplier: float = 1.0
    liquidity_thinning_pct: float = 0.0
    geographic_gap: bool = False
    evidence: List[str] = field(default_factory=list)


class TemporalAnalyzer:
    """Analyzes temporal patterns to predict high-risk windows for rug pulls,
    bot attacks, and liquidity drains.

    Uses historical attack frequency data, geographic gap detection, and
    known temporal windows to compute a real-time risk score (0-100).

    Self-improving: confirmed rug observations are added to the temporal
    database, which refines future predictions.
    """

    def __init__(self, db_path: Path = TEMPORAL_DB_FILE):
        """Initialize the temporal analyzer and load the pattern database.

        Args:
            db_path: Path to the temporal_patterns.json database file.
        """
        self.db_path = db_path
        self._db: Dict[str, Any] = {}
        self._load_db()

    # ─── Database Persistence ────────────────────────────────────────────

    def _load_db(self) -> None:
        """Load temporal patterns database from JSON file.

        Falls back to an empty skeleton structure if the file is missing
        or corrupted so that all analysis methods degrade gracefully.
        """
        try:
            if self.db_path.exists():
                self._db = json.loads(self.db_path.read_text(encoding="utf-8"))
                window_count = len(self._db.get("temporal_windows", []))
                logger.info(
                    "Loaded temporal patterns DB: %d windows, %d confirmed rugs",
                    window_count,
                    len(self._db.get("historical_confirmed_rugs", [])),
                )
            else:
                logger.warning("Temporal DB not found at %s — using empty defaults", self.db_path)
                self._db = self._empty_db()
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("Failed to load temporal DB: %s", exc)
            self._db = self._empty_db()

    @staticmethod
    def _empty_db() -> Dict[str, Any]:
        """Return a minimal valid database skeleton."""
        return {
            "version": "0.0.0",
            "last_updated": "",
            "temporal_windows": [],
            "hourly_attack_frequency": {},
            "day_of_week_attack_frequency": {},
            "geographic_gaps": [],
            "historical_confirmed_rugs": [],
        }

    def _save_db(self) -> None:
        """Persist the temporal patterns database back to JSON."""
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self.db_path.write_text(
                json.dumps(self._db, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            logger.debug("Saved temporal DB to %s", self.db_path)
        except OSError as exc:
            logger.error("Failed to save temporal DB: %s", exc)

    # ─── Helper Utilities ────────────────────────────────────────────────

    @staticmethod
    def _now_utc() -> datetime:
        """Return the current UTC time (timezone-aware)."""
        return datetime.now(timezone.utc)

    @staticmethod
    def _parse_utc_hour(time_str: str) -> int:
        """Parse an HH:MM UTC string and return the hour component.

        Args:
            time_str: Time string like "02:00" or "Friday 20:00".

        Returns:
            The hour integer (0-23).
        """
        # Handle compound strings like "Friday 20:00"
        parts = time_str.strip().split()
        time_part = parts[-1]  # last token is the HH:MM
        try:
            return int(time_part.split(":")[0])
        except (ValueError, IndexError):
            logger.warning("Cannot parse UTC hour from '%s'", time_str)
            return 0

    def _find_window(self, name: str) -> Optional[Dict[str, Any]]:
        """Look up a temporal window definition by name.

        Args:
            name: Window name, e.g. "rug_hour".

        Returns:
            The window dict or None.
        """
        for window in self._db.get("temporal_windows", []):
            if window.get("name") == name:
                return window
        return None

    def _is_in_time_range(self, current_hour: int, start_str: str, end_str: str) -> bool:
        """Check if *current_hour* falls within [start, end) UTC.

        Handles ranges that wrap across midnight (e.g. 22:00-04:00).

        Args:
            current_hour: Hour in UTC (0-23).
            start_str: Start time as "HH:MM".
            end_str: End time as "HH:MM".

        Returns:
            True if the current hour is inside the range.
        """
        start_h = self._parse_utc_hour(start_str)
        end_h = self._parse_utc_hour(end_str)

        if start_h <= end_h:
            return start_h <= current_hour < end_h
        else:
            # Wraps midnight, e.g. 22:00-04:00
            return current_hour >= start_h or current_hour < end_h

    # ─── Temporal Window Detectors ───────────────────────────────────────

    def detect_rug_hour(self) -> bool:
        """Check if the current UTC time falls in The Rug Hour (02:00-05:00 UTC).

        This is the most dangerous window — 78% of rug pulls happen here.
        US is asleep, Asia is tired, Europe is just waking up.

        Returns:
            True if currently inside The Rug Hour.
        """
        current_hour = self._now_utc().hour
        window = self._find_window("rug_hour")
        if window:
            return self._is_in_time_range(
                current_hour,
                window.get("start_utc", "02:00"),
                window.get("end_utc", "05:00"),
            )
        # Fallback to hardcoded range
        return 2 <= current_hour < 5

    def detect_sniper_window(self, token_launch_time: Optional[str] = None) -> bool:
        """Check if we are within the sniper window (0-5 min after token launch).

        Bots dominate 90% of buys in this window. Human buyers typically
        enter 30+ minutes later at already +50% markup.

        Args:
            token_launch_time: ISO 8601 timestamp of token launch (e.g.
                "2026-08-11T03:15:00Z"). If None, returns False.

        Returns:
            True if currently within the sniper window.
        """
        if not token_launch_time:
            return False

        try:
            launch_dt = datetime.fromisoformat(
                token_launch_time.replace("Z", "+00:00")
            )
            now = self._now_utc()
            elapsed_minutes = (now - launch_dt).total_seconds() / 60.0

            window = self._find_window("sniper_window")
            threshold = window.get("window_minutes_after_launch", 5) if window else 5

            return 0 <= elapsed_minutes <= threshold
        except (ValueError, TypeError) as exc:
            logger.warning("Failed to parse token launch time '%s': %s", token_launch_time, exc)
            return False

    def detect_fomo_peak(self) -> bool:
        """Check if we're in the FOMO Peak window (18:00-22:00 UTC).

        US evening — highest social activity. Prices often peak here,
        followed by overnight dumps (65% probability).

        Returns:
            True if currently inside FOMO Peak.
        """
        current_hour = self._now_utc().hour
        window = self._find_window("fomo_peak")
        if window:
            return self._is_in_time_range(
                current_hour,
                window.get("start_utc", "18:00"),
                window.get("end_utc", "22:00"),
            )
        return 18 <= current_hour < 22

    def detect_dead_zone(self) -> bool:
        """Check if we're in the Dead Zone (08:00-12:00 UTC).

        Lowest global activity. Hard to exit large positions.
        Slippage is 2.5× normal.

        Returns:
            True if currently inside the Dead Zone.
        """
        current_hour = self._now_utc().hour
        window = self._find_window("dead_zone")
        if window:
            return self._is_in_time_range(
                current_hour,
                window.get("start_utc", "08:00"),
                window.get("end_utc", "12:00"),
            )
        return 8 <= current_hour < 12

    def detect_weekend_trap(self) -> bool:
        """Check if we're in the Weekend Trap (Friday 20:00 - Monday 08:00 UTC).

        Lower moderation, 2× more scam launches, 50% fewer traders online.

        Returns:
            True if currently inside the Weekend Trap.
        """
        now = self._now_utc()
        day = now.weekday()  # Monday=0 … Sunday=6
        hour = now.hour

        window = self._find_window("weekend_trap")
        if window:
            start_str = window.get("start_utc", "Friday 20:00")
            end_str = window.get("end_utc", "Monday 08:00")
            start_day_name, start_hour = self._parse_day_hour(start_str)
            end_day_name, end_hour = self._parse_day_hour(end_str)
            start_dow = self._day_name_to_dow(start_day_name)
            end_dow = self._day_name_to_dow(end_day_name)
        else:
            start_dow, start_hour = 4, 20   # Friday = 4
            end_dow, end_hour = 0, 8         # Monday = 0

        # Convert to a comparable linear scale: (day_of_week * 24 + hour)
        current_pos = day * 24 + hour
        start_pos = start_dow * 24 + start_hour
        end_pos = end_dow * 24 + end_hour

        if start_pos <= end_pos:
            return start_pos <= current_pos < end_pos
        else:
            # Wraps across week boundary
            return current_pos >= start_pos or current_pos < end_pos

    @staticmethod
    def _parse_day_hour(time_str: str) -> Tuple[str, int]:
        """Parse 'Friday 20:00' → ('Friday', 20)."""
        parts = time_str.strip().split()
        if len(parts) >= 2:
            day_name = parts[0]
            try:
                hour = int(parts[1].split(":")[0])
            except (ValueError, IndexError):
                hour = 0
            return day_name, hour
        return "", 0

    @staticmethod
    def _day_name_to_dow(name: str) -> int:
        """Convert English day name to Python weekday (Monday=0)."""
        mapping = {
            "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
            "friday": 4, "saturday": 5, "sunday": 6,
        }
        return mapping.get(name.lower(), 0)

    def detect_golden_hour(self) -> bool:
        """Check if we're in the Golden Hour (14:00-16:00 UTC).

        US morning + Europe afternoon. Best liquidity (150% of average),
        80% organic volume. This is the optimal entry window.

        Returns:
            True if currently inside the Golden Hour.
        """
        current_hour = self._now_utc().hour
        window = self._find_window("golden_hour")
        if window:
            return self._is_in_time_range(
                current_hour,
                window.get("start_utc", "14:00"),
                window.get("end_utc", "16:00"),
            )
        return 14 <= current_hour < 16

    # ─── Risk Scoring ────────────────────────────────────────────────────

    def get_current_risk_window(self) -> List[str]:
        """Return a list of named temporal windows that are currently active.

        Returns:
            List of window names like ["rug_hour", "weekend_trap"].
        """
        active: List[str] = []
        if self.detect_rug_hour():
            active.append("rug_hour")
        if self.detect_fomo_peak():
            active.append("fomo_peak")
        if self.detect_dead_zone():
            active.append("dead_zone")
        if self.detect_weekend_trap():
            active.append("weekend_trap")
        if self.detect_golden_hour():
            active.append("golden_hour")
        return active

    def calculate_hourly_risk_score(self) -> float:
        """Calculate a risk score (0-100) for the current UTC hour.

        Combines:
        - Base score from active temporal windows
        - Attack frequency multiplier from historical data
        - Geographic gap bonus
        - Weekend bonus

        Returns:
            Risk score clamped to [0, 100].
        """
        now = self._now_utc()
        hour_key = f"{now.hour:02d}"
        day_key = str(now.weekday())

        # Base score from active windows
        base_score = 0.0
        active_windows = self.get_current_risk_window()
        for window_name in active_windows:
            window = self._find_window(window_name)
            if window:
                base_score += window.get("risk_score_base", 0)
            else:
                # Fallback defaults
                fallback_scores = {
                    "rug_hour": 40, "sniper_window": 30, "fomo_peak": 25,
                    "dead_zone": 20, "weekend_trap": 15, "golden_hour": 5,
                }
                base_score += fallback_scores.get(window_name, 0)

        # Golden hour reduces risk
        if "golden_hour" in active_windows:
            base_score = max(base_score - 15, 0)

        # Attack frequency multiplier
        hourly_freq = self._db.get("hourly_attack_frequency", {})
        daily_freq = self._db.get("day_of_week_attack_frequency", {})
        hour_mult = hourly_freq.get(hour_key, 1.0)
        day_mult = daily_freq.get(day_key, 1.0)
        combined_mult = hour_mult * day_mult

        # If combined multiplier >= 3×, add +40
        if combined_mult >= 3.0:
            base_score += SCORE_ATTACK_FREQUENCY_3X
        elif combined_mult >= 2.0:
            base_score += SCORE_ATTACK_FREQUENCY_3X * 0.5

        # Geographic gap bonus
        if self._has_geographic_gap(now.hour):
            base_score += SCORE_GEOGRAPHIC_GAP

        # Weekend bonus (already covered by weekend_trap window, but add
        # an independent check for partial weekend scoring)
        if now.weekday() in WEEKEND_DAYS and "weekend_trap" not in active_windows:
            base_score += SCORE_WEEKEND * 0.5

        return min(max(base_score, 0.0), 100.0)

    def _has_geographic_gap(self, hour_utc: int) -> bool:
        """Check if the given hour falls in a geographic gap window.

        A geographic gap occurs when all major crypto regions are offline
        or at low activity, leaving no organic buyer support.

        Args:
            hour_utc: Hour in UTC (0-23).

        Returns:
            True if a geographic gap is active.
        """
        for gap in self._db.get("geographic_gaps", []):
            window_str = gap.get("utc_window", "")
            try:
                start_str, end_str = window_str.split("-")
                if self._is_in_time_range(hour_utc, start_str, end_str):
                    return True
            except ValueError:
                continue
        return False

    def _get_liquidity_thinning(self, hour_utc: int) -> float:
        """Estimate liquidity thinning percentage for a given hour.

        Uses the rug_hour window's liquidity_thinning_pct as the reference
        and scales other hours proportionally based on attack frequency.

        Args:
            hour_utc: Hour in UTC (0-23).

        Returns:
            Estimated thinning percentage (0-100).
        """
        window = self._find_window("rug_hour")
        if window:
            max_thinning = window.get("liquidity_thinning_pct", 60)
        else:
            max_thinning = 60

        hourly_freq = self._db.get("hourly_attack_frequency", {})
        current_freq = hourly_freq.get(f"{hour_utc:02d}", 1.0)

        # Scale: at peak frequency (3.5) → max_thinning; at baseline (1.0) → 0
        if current_freq <= 1.0:
            return 0.0
        scaling = (current_freq - 1.0) / (3.5 - 1.0)
        return min(scaling * max_thinning, 100.0)

    def _get_geographic_gap_multiplier(self, hour_utc: int) -> float:
        """Return the risk multiplier from active geographic gaps.

        Args:
            hour_utc: Hour in UTC (0-23).

        Returns:
            Risk multiplier (1.0 = no gap).
        """
        for gap in self._db.get("geographic_gaps", []):
            window_str = gap.get("utc_window", "")
            try:
                start_str, end_str = window_str.split("-")
                if self._is_in_time_range(hour_utc, start_str, end_str):
                    return gap.get("risk_multiplier", 1.0)
            except ValueError:
                continue
        return 1.0

    # ─── Comprehensive Temporal Analysis ─────────────────────────────────

    def calculate_temporal_risk(
        self,
        token_launch_time: Optional[str] = None,
        chain: Optional[str] = None,
    ) -> TemporalRiskResult:
        """Perform comprehensive temporal risk analysis.

        This is the main entry point that runs all detectors and aggregates
        results into a single TemporalRiskResult.

        Args:
            token_launch_time: ISO 8601 timestamp of token launch. Used for
                sniper window detection. Optional.
            chain: Blockchain identifier (e.g. "eth", "solana"). Used for
                historical pattern matching. Optional.

        Returns:
            A TemporalRiskResult with the full analysis.
        """
        now = self._now_utc()
        result = TemporalRiskResult(
            current_utc_time=now.isoformat(),
        )

        # ── Run all detectors ─────────────────────────────────────────
        result.is_rug_hour = self.detect_rug_hour()
        result.is_fomo_peak = self.detect_fomo_peak()
        result.is_dead_zone = self.detect_dead_zone()
        result.is_weekend_trap = self.detect_weekend_trap()
        result.is_golden_hour = self.detect_golden_hour()

        is_sniper = self.detect_sniper_window(token_launch_time)

        # ── Collect active windows ────────────────────────────────────
        active = self.get_current_risk_window()
        if is_sniper:
            active.append("sniper_window")
        result.active_windows = active

        # ── Attack frequency multiplier ──────────────────────────────
        hour_key = f"{now.hour:02d}"
        day_key = str(now.weekday())
        hourly_freq = self._db.get("hourly_attack_frequency", {})
        daily_freq = self._db.get("day_of_week_attack_frequency", {})
        hour_mult = hourly_freq.get(hour_key, 1.0)
        day_mult = daily_freq.get(day_key, 1.0)
        result.attack_frequency_multiplier = round(hour_mult * day_mult, 2)

        # ── Geographic gap ───────────────────────────────────────────
        result.geographic_gap = self._has_geographic_gap(now.hour)
        gap_mult = self._get_geographic_gap_multiplier(now.hour)

        # ── Liquidity thinning ───────────────────────────────────────
        result.liquidity_thinning_pct = round(
            self._get_liquidity_thinning(now.hour), 1
        )

        # ── Calculate composite risk score ───────────────────────────
        risk = 0.0
        evidence: List[str] = []

        # Component 1: Active window base scores
        for window_name in active:
            window = self._find_window(window_name)
            base = window.get("risk_score_base", 0) if window else {
                "rug_hour": 40, "sniper_window": 30, "fomo_peak": 25,
                "dead_zone": 20, "weekend_trap": 15, "golden_hour": 5,
            }.get(window_name, 0)
            risk += base
            evidence.append(f"Active window: {window_name} (+{base})")

        # Golden hour is protective — subtract from risk
        if result.is_golden_hour:
            reduction = 15
            risk = max(risk - reduction, 0)
            evidence.append(f"Golden Hour protection (−{reduction})")

        # Component 2: Historical attack frequency 3×+ baseline = +40
        if result.attack_frequency_multiplier >= 3.0:
            risk += SCORE_ATTACK_FREQUENCY_3X
            evidence.append(
                f"Attack frequency {result.attack_frequency_multiplier:.1f}× "
                f"baseline (≥3× → +{SCORE_ATTACK_FREQUENCY_3X})"
            )
        elif result.attack_frequency_multiplier >= 2.0:
            partial = SCORE_ATTACK_FREQUENCY_3X * 0.5
            risk += partial
            evidence.append(
                f"Attack frequency {result.attack_frequency_multiplier:.1f}× "
                f"baseline (≥2× → +{partial:.0f})"
            )

        # Component 3: Liquidity thins >50% vs daytime = +25
        if result.liquidity_thinning_pct > 50:
            risk += SCORE_LIQUIDITY_THIN_50PCT
            evidence.append(
                f"Liquidity thinning {result.liquidity_thinning_pct:.0f}% "
                f"(>50% → +{SCORE_LIQUIDITY_THIN_50PCT})"
            )
        elif result.liquidity_thinning_pct > 25:
            partial = SCORE_LIQUIDITY_THIN_50PCT * 0.5
            risk += partial
            evidence.append(
                f"Liquidity thinning {result.liquidity_thinning_pct:.0f}% "
                f"(>25% → +{partial:.0f})"
            )

        # Component 4: Geographic gap = +20
        if result.geographic_gap:
            risk += SCORE_GEOGRAPHIC_GAP
            evidence.append(
                f"Geographic gap active (gap multiplier {gap_mult:.1f}× → "
                f"+{SCORE_GEOGRAPHIC_GAP})"
            )

        # Component 5: Weekend = +15
        if result.is_weekend_trap:
            risk += SCORE_WEEKEND
            evidence.append(f"Weekend trap active → +{SCORE_WEEKEND}")

        # Component 6: Holiday check (basic — can be extended)
        holiday_bonus = self._check_holiday(now)
        if holiday_bonus:
            risk += SCORE_HOLIDAY
            evidence.append(f"Major holiday ({holiday_bonus}) → +{SCORE_HOLIDAY}")

        # Component 7: Sniper window additional risk
        if is_sniper:
            risk += 30
            evidence.append("Sniper window active (0-5 min post-launch) → +30")

        # Component 8: Chain-specific historical rug frequency
        if chain:
            chain_risk = self._chain_historical_risk(chain, now.hour, now.weekday())
            if chain_risk > 0:
                risk += chain_risk
                evidence.append(f"Chain '{chain}' historical pattern → +{chain_risk:.0f}")

        # Clamp and assign
        result.risk_score = round(min(max(risk, 0.0), 100.0), 1)
        result.evidence = evidence

        # ── Generate recommendations ─────────────────────────────────
        result.recommendations = self._generate_recommendations(result)

        return result

    def _check_holiday(self, dt: datetime) -> Optional[str]:
        """Check if the given date falls on a major US/EU/Asia holiday.

        This is a simplified check for well-known crypto-impacting holidays.
        Can be extended with a proper holiday library.

        Args:
            dt: The datetime to check (UTC).

        Returns:
            Holiday name if found, else None.
        """
        month = dt.month
        day = dt.day

        # Simplified: check month/day against fixed-date holidays
        holidays = {
            (1, 1): "New Year's Day",
            (7, 4): "US Independence Day",
            (12, 25): "Christmas",
            (12, 26): "Boxing Day",
            (1, 29): "Lunar New Year (approx)",
        }
        return holidays.get((month, day))

    def _chain_historical_risk(
        self, chain: str, hour_utc: int, day_of_week: int
    ) -> float:
        """Estimate additional risk from chain-specific historical rug data.

        Analyzes confirmed rugs on the same chain and checks how many
        occurred in the same hour/day-of-week pattern.

        Args:
            chain: Blockchain identifier (e.g. "eth", "solana").
            hour_utc: Current hour in UTC.
            day_of_week: Current day of week (Monday=0).

        Returns:
            Additional risk score (0-15).
        """
        rugs = self._db.get("historical_confirmed_rugs", [])
        if not rugs:
            return 0.0

        matching = 0
        for rug in rugs:
            if rug.get("chain", "").lower() != chain.lower():
                continue
            try:
                rug_dt = datetime.fromisoformat(
                    rug.get("date", "").replace("Z", "+00:00")
                )
                # Same hour or adjacent hour ±1
                if abs(rug_dt.hour - hour_utc) <= 1:
                    matching += 1
                # Same day of week
                elif rug_dt.weekday() == day_of_week:
                    matching += 0.5
            except (ValueError, TypeError):
                continue

        # Scale: each matching rug adds up to 5, capped at 15
        return min(matching * 5, 15.0)

    def _generate_recommendations(self, result: TemporalRiskResult) -> List[str]:
        """Generate actionable recommendations based on the temporal risk result.

        Args:
            result: The computed temporal risk result.

        Returns:
            List of human-readable recommendation strings.
        """
        recs: List[str] = []

        if result.is_rug_hour:
            recs.append(
                "⚠ RUG HOUR ACTIVE — 78% of rug pulls happen in this window. "
                "Avoid new entries. Set tight stop-losses."
            )
        if result.is_fomo_peak:
            recs.append(
                "FOMO PEAK — Social volume is highest but overnight dump probability "
                "is 65%. Take partial profits if up."
            )
        if result.is_dead_zone:
            recs.append(
                "DEAD ZONE — Liquidity is thin, slippage 2.5× normal. "
                "Avoid large market sells."
            )
        if result.is_weekend_trap:
            recs.append(
                "WEEKEND TRAP — 2× scam launches, 40% less moderation. "
                "Verify contracts extra carefully."
            )
        if "sniper_window" in result.active_windows:
            recs.append(
                "🤖 SNIPER WINDOW — Bot dominance at 90%. Do NOT buy in the first "
                "5 minutes. Wait 30+ min for human entry point."
            )
        if result.geographic_gap:
            recs.append(
                "GEOGRAPHIC GAP — Major regions offline. No organic buyer support. "
                "Extreme caution."
            )
        if result.is_golden_hour and result.risk_score < 30:
            recs.append(
                "✦ GOLDEN HOUR — Best entry window. 150% liquidity, 80% organic volume. "
                "Favorable conditions for new positions."
            )

        # Risk-tiered overall guidance
        if result.risk_score >= 80:
            recs.append(
                "🚨 CRITICAL RISK — Do not enter new positions. Consider exiting "
                "existing memecoin positions."
            )
        elif result.risk_score >= 60:
            recs.append(
                "HIGH RISK — Only enter with small positions and tight stop-losses. "
                "Verify all contracts."
            )
        elif result.risk_score >= 40:
            recs.append(
                "MODERATE RISK — Exercise caution. Use limit orders, avoid market buys."
            )
        elif result.risk_score < 20:
            recs.append(
                "LOW RISK — Relatively safe window. Standard caution applies."
            )

        return recs

    # ─── Predictive Methods ──────────────────────────────────────────────

    def predict_attack_frequency(
        self, hour_utc: int, day_of_week: int
    ) -> float:
        """Predict the attack frequency multiplier for a given hour and day.

        Uses historical hourly and day-of-week attack frequency data from
        the temporal patterns database. The prediction is the product of
        the hourly multiplier and the day-of-week multiplier.

        Args:
            hour_utc: Hour of day in UTC (0-23).
            day_of_week: Day of week (Monday=0, Sunday=6).

        Returns:
            Predicted attack frequency multiplier. 1.0 = baseline.
            Higher values indicate more danger.
        """
        hourly_freq = self._db.get("hourly_attack_frequency", {})
        daily_freq = self._db.get("day_of_week_attack_frequency", {})

        hour_key = f"{hour_utc % 24:02d}"
        day_key = str(day_of_week % 7)

        hour_mult = hourly_freq.get(hour_key, 1.0)
        day_mult = daily_freq.get(day_key, 1.0)

        prediction = hour_mult * day_mult

        logger.debug(
            "Attack frequency prediction for hour=%s dow=%s: "
            "hour_mult=%.2f × day_mult=%.2f = %.2f",
            hour_key, day_key, hour_mult, day_mult, prediction,
        )

        return round(prediction, 2)

    # ─── Self-Improving (Learning) ───────────────────────────────────────

    def add_confirmed_rug_observation(self, observation: Dict[str, Any]) -> None:
        """Add a confirmed rug pull observation to the temporal database.

        This is the self-improving mechanism: as more rugs are confirmed,
        the temporal patterns become more accurate for future predictions.

        The observation is also used to update hourly and day-of-week
        attack frequency data, nudging them slightly upward for the
        time window where the rug occurred.

        Args:
            observation: Dict with at least:
                - project (str): Token name/symbol
                - date (str): ISO 8601 timestamp of the rug
                - rug_type (str): "hard_rug" or "soft_rug"
                - chain (str): Blockchain identifier
                - loss_usd (float/int): Total loss in USD
                - dev_address (str): Developer wallet address
        """
        required_keys = {"project", "date", "rug_type", "chain"}
        missing = required_keys - set(observation.keys())
        if missing:
            logger.warning(
                "Rug observation missing required keys: %s — skipping", missing
            )
            return

        # Add to confirmed rugs list
        rugs = self._db.setdefault("historical_confirmed_rugs", [])
        rugs.append({
            "project": observation["project"],
            "date": observation["date"],
            "rug_type": observation["rug_type"],
            "chain": observation["chain"],
            "loss_usd": observation.get("loss_usd", 0),
            "dev_address": observation.get("dev_address", ""),
        })

        # Update attack frequency data based on the rug's timestamp
        try:
            rug_dt = datetime.fromisoformat(
                observation["date"].replace("Z", "+00:00")
            )
            hour_key = f"{rug_dt.hour:02d}"
            day_key = str(rug_dt.weekday())

            # Nudge hourly frequency up by 2% (learning rate)
            hourly_freq = self._db.setdefault("hourly_attack_frequency", {})
            current_hourly = hourly_freq.get(hour_key, 1.0)
            hourly_freq[hour_key] = round(current_hourly * 1.02, 2)

            # Nudge day-of-week frequency up by 2%
            daily_freq = self._db.setdefault("day_of_week_attack_frequency", {})
            current_daily = daily_freq.get(day_key, 1.0)
            daily_freq[day_key] = round(current_daily * 1.02, 2)

            logger.info(
                "Added confirmed rug observation: %s (%s) at %s. "
                "Updated freq for hour=%s, dow=%s",
                observation["project"],
                observation["rug_type"],
                observation["date"],
                hour_key,
                day_key,
            )
        except (ValueError, TypeError) as exc:
            logger.warning(
                "Could not parse rug date '%s' for frequency update: %s",
                observation.get("date", ""), exc,
            )

        # Update metadata
        self._db["last_updated"] = self._now_utc().isoformat()

        # Persist to disk
        self._save_db()

    # ─── Statistics / Introspection ──────────────────────────────────────

    def get_historical_rug_count(self, chain: Optional[str] = None) -> int:
        """Return the count of confirmed historical rugs, optionally filtered by chain.

        Args:
            chain: If provided, only count rugs on this chain.

        Returns:
            Number of matching confirmed rugs.
        """
        rugs = self._db.get("historical_confirmed_rugs", [])
        if chain:
            return sum(
                1 for r in rugs
                if r.get("chain", "").lower() == chain.lower()
            )
        return len(rugs)

    def get_peak_danger_hours(self, threshold: float = 2.5) -> List[Tuple[int, float]]:
        """Return hours where attack frequency exceeds the threshold.

        Args:
            threshold: Minimum frequency multiplier to include.

        Returns:
            List of (hour, frequency) tuples sorted by frequency descending.
        """
        hourly_freq = self._db.get("hourly_attack_frequency", {})
        peaks = []
        for hour_str, freq in hourly_freq.items():
            if freq >= threshold:
                try:
                    hour = int(hour_str)
                    peaks.append((hour, freq))
                except ValueError:
                    continue
        peaks.sort(key=lambda x: x[1], reverse=True)
        return peaks

    def get_safest_hours(self, threshold: float = 1.0) -> List[Tuple[int, float]]:
        """Return hours where attack frequency is at or below the threshold.

        Args:
            threshold: Maximum frequency multiplier to include.

        Returns:
            List of (hour, frequency) tuples sorted by frequency ascending.
        """
        hourly_freq = self._db.get("hourly_attack_frequency", {})
        safe = []
        for hour_str, freq in hourly_freq.items():
            if freq <= threshold:
                try:
                    hour = int(hour_str)
                    safe.append((hour, freq))
                except ValueError:
                    continue
        safe.sort(key=lambda x: x[1])
        return safe
