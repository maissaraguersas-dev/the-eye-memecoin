"""THE EYE — Developer Rug Signature Matcher

Detects 7 rug pull developer signatures:
1. Soft Rug — gradual sell over days (harder to detect)
2. Hard Rug — single massive sell or liquidity removal
3. Honey Pot — buy works but sell is blocked
4. Mint Exploit — dev can mint unlimited tokens
5. Proxy Rug — upgradeable contract that changes rules post-launch
6. Serial Rugger — same dev address deployed multiple rugs
7. Social-Only Rug — no code, pure social manipulation
"""
import json
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

from config.settings import settings


class DevRugSignature(Enum):
    SOFT_RUG = "soft_rug"
    HARD_RUG = "hard_rug"
    HONEY_POT = "honey_pot"
    MINT_EXPLOIT = "mint_exploit"
    PROXY_RUG = "proxy_rug"
    SERIAL_RUGGER = "serial_rugger"
    SOCIAL_ONLY_RUG = "social_only_rug"


@dataclass
class DevProfile:
    address: str
    chain: str
    deployments: int = 0
    rugs_confirmed: int = 0
    rugs_suspected: int = 0
    avg_token_lifetime_hours: float = 0.0
    wallet_age_days: float = 0.0
    total_supply_held_pct: float = 0.0
    is_fresh_wallet: bool = False
    has_removed_liquidity: bool = False
    uses_proxy_contract: bool = False
    can_mint: bool = False
    known_associates: list[str] = field(default_factory=list)
    last_active: float = 0.0
    confidence: float = 0.0


@dataclass
class DevMatchResult:
    dev_address: str
    signature: DevRugSignature
    confidence: float
    rug_probability_add: float  # how much this adds to rug probability
    description: str
    evidence: list[str] = field(default_factory=list)
    timestamp: float = 0.0


class DevMatcher:
    """Match developer behavior to known rug pull signatures."""

    DATA_DIR = Path(__file__).parent.parent / "data"
    SIGNATURES_FILE = DATA_DIR / "dev_signatures.json"

    def __init__(self):
        self.dev_profiles: dict[str, DevProfile] = {}
        self._load_profiles()

    def _load_profiles(self):
        if self.SIGNATURES_FILE.exists():
            with open(self.SIGNATURES_FILE) as f:
                data = json.load(f)
            for addr, prof in data.items():
                self.dev_profiles[addr] = DevProfile(
                    address=addr,
                    chain=prof.get("chain", "eth"),
                    deployments=prof.get("deployments", 0),
                    rugs_confirmed=prof.get("rugs_confirmed", 0),
                    rugs_suspected=prof.get("rugs_suspected", 0),
                    avg_token_lifetime_hours=prof.get("avg_token_lifetime_hours", 0),
                    wallet_age_days=prof.get("wallet_age_days", 0),
                    total_supply_held_pct=prof.get("total_supply_held_pct", 0),
                    is_fresh_wallet=prof.get("is_fresh_wallet", False),
                    has_removed_liquidity=prof.get("has_removed_liquidity", False),
                    uses_proxy_contract=prof.get("uses_proxy_contract", False),
                    can_mint=prof.get("can_mint", False),
                    last_active=prof.get("last_active", 0),
                    confidence=prof.get("confidence", 0),
                )

    def _save_profiles(self):
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        data = {}
        for addr, prof in self.dev_profiles.items():
            data[addr] = {
                "chain": prof.chain,
                "deployments": prof.deployments,
                "rugs_confirmed": prof.rugs_confirmed,
                "rugs_suspected": prof.rugs_suspected,
                "avg_token_lifetime_hours": prof.avg_token_lifetime_hours,
                "wallet_age_days": prof.wallet_age_days,
                "total_supply_held_pct": prof.total_supply_held_pct,
                "is_fresh_wallet": prof.is_fresh_wallet,
                "has_removed_liquidity": prof.has_removed_liquidity,
                "uses_proxy_contract": prof.uses_proxy_contract,
                "can_mint": prof.can_mint,
                "last_active": prof.last_active,
                "confidence": prof.confidence,
            }
        with open(self.SIGNATURES_FILE, "w") as f:
            json.dump(data, f, indent=2)

    # ── Pattern Detection ───────────────────────────────────────────

    def detect_soft_rug(self, dev: DevProfile) -> Optional[DevMatchResult]:
        """Soft Rug: dev gradually sells over days — harder to spot."""
        if (dev.total_supply_held_pct > 5 and
            dev.has_removed_liquidity is False and
            dev.avg_token_lifetime_hours > 48 and
            dev.rugs_suspected > 0):
            confidence = min(80, 30 + dev.rugs_suspected * 15)
            return DevMatchResult(
                dev_address=dev.address,
                signature=DevRugSignature.SOFT_RUG,
                confidence=confidence,
                rug_probability_add=min(25, dev.rugs_suspected * 10),
                description=f"Soft rug pattern: dev holds {dev.total_supply_held_pct:.1f}%, "
                           f"gradual selling suspected",
                evidence=[f"Holds {dev.total_supply_held_pct:.1f}% supply",
                         f"Avg token lifetime {dev.avg_token_lifetime_hours:.0f}h"],
                timestamp=time.time(),
            )
        return None

    def detect_hard_rug(self, dev: DevProfile) -> Optional[DevMatchResult]:
        """Hard Rug: sudden liquidity removal or massive sell."""
        if dev.has_removed_liquidity or (dev.rugs_confirmed > 0 and dev.avg_token_lifetime_hours < 24):
            confidence = min(95, 50 + dev.rugs_confirmed * 20)
            return DevMatchResult(
                dev_address=dev.address,
                signature=DevRugSignature.HARD_RUG,
                confidence=confidence,
                rug_probability_add=40,
                description=f"Hard rug signature: {'removed liquidity' if dev.has_removed_liquidity else 'confirmed rugs'}",
                evidence=[f"Rugs confirmed: {dev.rugs_confirmed}",
                         f"Liquidity removed: {dev.has_removed_liquidity}"],
                timestamp=time.time(),
            )
        return None

    def detect_honey_pot(self, dev: DevProfile) -> Optional[DevMatchResult]:
        """Honey Pot: buy works but sell is blocked at contract level."""
        # Would need contract interaction test
        if dev.can_mint and dev.deployments >= 1:
            confidence = 60
            return DevMatchResult(
                dev_address=dev.address,
                signature=DevRugSignature.HONEY_POT,
                confidence=confidence,
                rug_probability_add=35,
                description="Potential honey pot: mint function + no sell test yet",
                evidence=["Has mint function", "Needs sell simulation"],
                timestamp=time.time(),
            )
        return None

    def detect_mint_exploit(self, dev: DevProfile) -> Optional[DevMatchResult]:
        """Mint Exploit: dev can mint unlimited tokens, diluting holders."""
        if dev.can_mint:
            return DevMatchResult(
                dev_address=dev.address,
                signature=DevRugSignature.MINT_EXPLOIT,
                confidence=75,
                rug_probability_add=30,
                description="Mint exploit: dev can mint unlimited tokens",
                evidence=["Owner mint function detected"],
                timestamp=time.time(),
            )
        return None

    def detect_proxy_rug(self, dev: DevProfile) -> Optional[DevMatchResult]:
        """Proxy Rug: upgradeable proxy contract — rules can change after launch."""
        if dev.uses_proxy_contract:
            return DevMatchResult(
                dev_address=dev.address,
                signature=DevRugSignature.PROXY_RUG,
                confidence=70,
                rug_probability_add=25,
                description="Proxy rug risk: upgradeable contract detected",
                evidence=["Proxy contract pattern found"],
                timestamp=time.time(),
            )
        return None

    def detect_serial_rugger(self, dev: DevProfile) -> Optional[DevMatchResult]:
        """Serial Rugger: same dev deployed multiple rugs before."""
        if dev.rugs_confirmed >= 2 or (dev.rugs_suspected >= 3):
            confidence = min(95, 60 + dev.rugs_confirmed * 15)
            return DevMatchResult(
                dev_address=dev.address,
                signature=DevRugSignature.SERIAL_RUGGER,
                confidence=confidence,
                rug_probability_add=40,
                description=f"Serial rugger: {dev.rugs_confirmed} confirmed, "
                           f"{dev.rugs_suspected} suspected rugs",
                evidence=[f"Confirmed rugs: {dev.rugs_confirmed}",
                         f"Suspected rugs: {dev.rugs_suspected}",
                         f"Total deployments: {dev.deployments}"],
                timestamp=time.time(),
            )
        return None

    def detect_social_only_rug(self, dev: DevProfile) -> Optional[DevMatchResult]:
        """Social-Only Rug: no real code, just social manipulation."""
        if dev.deployments == 0 and dev.is_fresh_wallet:
            confidence = 50
            return DevMatchResult(
                dev_address=dev.address,
                signature=DevRugSignature.SOCIAL_ONLY_RUG,
                confidence=confidence,
                rug_probability_add=15,
                description="Social-only rug: fresh wallet with no deployment history",
                evidence=["Fresh wallet", "No verified deployments"],
                timestamp=time.time(),
            )
        return None

    # ── Full Analysis ───────────────────────────────────────────────

    def analyze_dev(self, dev_address: str, chain: str = "eth") -> list[DevMatchResult]:
        """Run all 7 signature detections on a developer address."""
        dev = self.dev_profiles.get(dev_address, DevProfile(address=dev_address, chain=chain))
        results = []

        detectors = [
            self.detect_soft_rug,
            self.detect_hard_rug,
            self.detect_honey_pot,
            self.detect_mint_exploit,
            self.detect_proxy_rug,
            self.detect_serial_rugger,
            self.detect_social_only_rug,
        ]

        for detector in detectors:
            match = detector(dev)
            if match:
                results.append(match)

        return results

    def get_total_rug_probability_add(self, dev_address: str, chain: str = "eth") -> float:
        """Sum all rug probability additions from detected signatures."""
        results = self.analyze_dev(dev_address, chain)
        total = sum(r.rug_probability_add for r in results)
        return min(total, 100)  # cap at 100%

    def update_dev_profile(self, address: str, chain: str = "eth", **kwargs):
        """Update a dev profile — learning mechanism."""
        if address not in self.dev_profiles:
            self.dev_profiles[address] = DevProfile(address=address, chain=chain)
        dev = self.dev_profiles[address]
        for k, v in kwargs.items():
            if hasattr(dev, k):
                setattr(dev, k, v)
        dev.last_active = time.time()
        self._save_profiles()

    def flag_rug(self, dev_address: str, confirmed: bool = True):
        """Flag a developer as a confirmed or suspected rugger — learning."""
        if dev_address in self.dev_profiles:
            if confirmed:
                self.dev_profiles[dev_address].rugs_confirmed += 1
            else:
                self.dev_profiles[dev_address].rugs_suspected += 1
            self._save_profiles()
