"""
Mock government verification providers (Day 4).

Each provider implements the same `VerificationProvider` interface so the
verification_service can call any of them uniformly, and so a real government
API integration can be dropped in later (post-hackathon) by writing one new
class per provider without touching the rule engine or verification_service.

*** MOCK DATA DISCLAIMER ***
Every provider here reads from static dummy datasets in mock_verification_data.py.
NONE of this scrapes, calls, or represents any real government website or API
(GSTN, Udyam, MCA21, BIS CareCert, GeM debarment list, etc). Every ProviderResult
carries `is_mock=True` and a human-readable `note` saying so. Do not remove
that disclaimer when wiring in a real provider later - flip `is_mock` to False
on the real subclass instead.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from app.models.verification import VerificationStatus
from app.services import mock_verification_data as mockdb


@dataclass
class ProviderResult:
    status: VerificationStatus
    data: Dict[str, Any] = field(default_factory=dict)
    note: str = ""
    provider_name: str = ""
    is_mock: bool = True


class VerificationProvider(ABC):
    """Interface every verification provider (mock or real) must implement."""

    name: str = "base_provider"

    @abstractmethod
    def verify(self, identifier: Optional[str], context: Dict[str, Any]) -> ProviderResult:
        """
        `identifier` is the value extracted from the bidder's document (GSTIN,
        PAN, Udyam number, CIN, BIS license number, or a company name for the
        blacklist check). `context` carries anything else useful (e.g. the
        bidder's company_name, for cross-checking legal names).
        Must never raise for "not found" - that's a normal ProviderResult,
        not an exception. Only raise for genuine programming errors.
        """
        raise NotImplementedError


class GSTVerificationProvider(VerificationProvider):
    """Mock GSTN lookup. Required condition: status == 'Active'."""

    name = "gst_mock"

    def verify(self, identifier, context):
        if not identifier:
            return ProviderResult(
                VerificationStatus.NOT_FOUND,
                note="No GSTIN could be read from the bidder's GST document.",
                provider_name=self.name,
            )
        key = identifier.strip().upper()
        record = mockdb.GST_DATABASE.get(key)
        if not record:
            return ProviderResult(
                VerificationStatus.NOT_FOUND,
                note=f"GSTIN {key} was not found in the mock GSTN dataset (MOCK DATA, not a real GST lookup).",
                provider_name=self.name,
            )
        ok = record["status"] == "Active"
        filing_status = record.get("return_filing_status", "Unknown")
        return ProviderResult(
            VerificationStatus.VERIFIED if ok else VerificationStatus.MISMATCH,
            data={"gstin": key, **record},
            note=(
                f"Mock GSTN registry shows GSTIN {key} status = '{record['status']}', "
                f"return filing status = '{filing_status}'."
            ),
            provider_name=self.name,
        )


class PANVerificationProvider(VerificationProvider):
    """Mock PAN existence/identity check."""

    name = "pan_mock"

    def verify(self, identifier, context):
        if not identifier:
            return ProviderResult(
                VerificationStatus.NOT_FOUND,
                note="No PAN could be read from the bidder's PAN document.",
                provider_name=self.name,
            )
        key = identifier.strip().upper()
        record = mockdb.PAN_DATABASE.get(key)
        if not record:
            return ProviderResult(
                VerificationStatus.NOT_FOUND,
                note=f"PAN {key} was not found in the mock PAN dataset (MOCK DATA, not a real ITD lookup).",
                provider_name=self.name,
            )
        declared_name = (context.get("company_name") or "").strip().upper()
        record_name = record["legal_name"].strip().upper()
        name_matches = (not declared_name) or declared_name in record_name or record_name in declared_name
        status = VerificationStatus.VERIFIED if (record["status"] == "Valid" and name_matches) else VerificationStatus.MISMATCH
        note = f"Mock PAN registry shows PAN {key} status = '{record['status']}', legal name = '{record['legal_name']}'."
        if not name_matches:
            note += f" This does not clearly match the bidder's declared name '{context.get('company_name')}'."
        return ProviderResult(status, data={"pan": key, **record}, note=note, provider_name=self.name)


class UdyamVerificationProvider(VerificationProvider):
    """Mock Udyam/MSME registration check."""

    name = "udyam_mock"

    def verify(self, identifier, context):
        if not identifier:
            return ProviderResult(
                VerificationStatus.NOT_FOUND,
                note="No Udyam registration number could be read from the bidder's document.",
                provider_name=self.name,
            )
        key = identifier.strip().upper()
        record = mockdb.UDYAM_DATABASE.get(key)
        if not record:
            return ProviderResult(
                VerificationStatus.NOT_FOUND,
                note=f"Udyam number {key} was not found in the mock Udyam dataset (MOCK DATA).",
                provider_name=self.name,
            )
        ok = record["status"] == "Active"
        return ProviderResult(
            VerificationStatus.VERIFIED if ok else VerificationStatus.MISMATCH,
            data={"udyam_registration_number": key, **record},
            note=f"Mock Udyam registry shows {key} status = '{record['status']}', category = '{record['enterprise_category']}'.",
            provider_name=self.name,
        )


class MCAVerificationProvider(VerificationProvider):
    """Mock MCA21 company master data check (CIN)."""

    name = "mca_mock"

    def verify(self, identifier, context):
        if not identifier:
            return ProviderResult(
                VerificationStatus.NOT_FOUND,
                note="No CIN could be read from the bidder's company registration document.",
                provider_name=self.name,
            )
        key = identifier.strip().upper()
        record = mockdb.MCA_DATABASE.get(key)
        if not record:
            return ProviderResult(
                VerificationStatus.NOT_FOUND,
                note=f"CIN {key} was not found in the mock MCA21 dataset (MOCK DATA, not a real MCA lookup).",
                provider_name=self.name,
            )
        ok = record["status"] == "Active"
        return ProviderResult(
            VerificationStatus.VERIFIED if ok else VerificationStatus.MISMATCH,
            data={"cin": key, **record},
            note=f"Mock MCA21 registry shows CIN {key} status = '{record['status']}'.",
            provider_name=self.name,
        )


class BISVerificationProvider(VerificationProvider):
    """Mock BIS license/CML validity check."""

    name = "bis_mock"

    def verify(self, identifier, context):
        if not identifier:
            return ProviderResult(
                VerificationStatus.NOT_FOUND,
                note="No BIS license number could be read from the bidder's BIS certificate.",
                provider_name=self.name,
            )
        key = identifier.strip().upper()
        record = mockdb.BIS_DATABASE.get(key)
        if not record:
            return ProviderResult(
                VerificationStatus.NOT_FOUND,
                note=f"BIS license {key} was not found in the mock BIS dataset (MOCK DATA, not a real BIS CareCert lookup).",
                provider_name=self.name,
            )
        ok = record["status"] == "Valid"
        return ProviderResult(
            VerificationStatus.VERIFIED if ok else VerificationStatus.MISMATCH,
            data={"bis_license_number": key, **record},
            note=f"Mock BIS registry shows license {key} status = '{record['status']}', valid upto {record['valid_upto']}.",
            provider_name=self.name,
        )


class EPFOVerificationProvider(VerificationProvider):
    """Mock EPFO establishment registration check."""

    name = "epfo_mock"

    def verify(self, identifier, context):
        if not identifier:
            return ProviderResult(
                VerificationStatus.NOT_FOUND,
                note="No EPFO establishment ID could be read from the bidder's document.",
                provider_name=self.name,
            )
        key = identifier.strip().upper()
        record = mockdb.EPFO_DATABASE.get(key)
        if not record:
            return ProviderResult(
                VerificationStatus.NOT_FOUND,
                note=f"EPFO establishment ID {key} was not found in the mock EPFO dataset (MOCK DATA).",
                provider_name=self.name,
            )
        ok = record["status"] == "Active"
        return ProviderResult(
            VerificationStatus.VERIFIED if ok else VerificationStatus.MISMATCH,
            data={"epfo_establishment_id": key, **record},
            note=f"Mock EPFO registry shows {key} status = '{record['status']}'.",
            provider_name=self.name,
        )


class ESICVerificationProvider(VerificationProvider):
    """Mock ESIC registration check."""

    name = "esic_mock"

    def verify(self, identifier, context):
        if not identifier:
            return ProviderResult(
                VerificationStatus.NOT_FOUND,
                note="No ESIC registration number could be read from the bidder's document.",
                provider_name=self.name,
            )
        key = identifier.strip().upper()
        record = mockdb.ESIC_DATABASE.get(key)
        if not record:
            return ProviderResult(
                VerificationStatus.NOT_FOUND,
                note=f"ESIC registration {key} was not found in the mock ESIC dataset (MOCK DATA).",
                provider_name=self.name,
            )
        ok = record["status"] == "Active"
        return ProviderResult(
            VerificationStatus.VERIFIED if ok else VerificationStatus.MISMATCH,
            data={"esic_registration_number": key, **record},
            note=f"Mock ESIC registry shows {key} status = '{record['status']}'.",
            provider_name=self.name,
        )


class StartupDPIITVerificationProvider(VerificationProvider):
    """Mock DPIIT Startup India recognition check."""

    name = "startup_dpiit_mock"

    def verify(self, identifier, context):
        if not identifier:
            return ProviderResult(
                VerificationStatus.NOT_FOUND,
                note="No DPIIT certificate number could be read from the bidder's document.",
                provider_name=self.name,
            )
        key = identifier.strip().upper()
        record = mockdb.STARTUP_DPIIT_DATABASE.get(key)
        if not record:
            return ProviderResult(
                VerificationStatus.NOT_FOUND,
                note=f"DPIIT certificate {key} was not found in the mock Startup India dataset (MOCK DATA).",
                provider_name=self.name,
            )
        ok = record["status"] == "Recognized"
        return ProviderResult(
            VerificationStatus.VERIFIED if ok else VerificationStatus.MISMATCH,
            data={"dpiit_certificate_number": key, **record},
            note=f"Mock Startup India registry shows {key} status = '{record['status']}'.",
            provider_name=self.name,
        )


class NSICVerificationProvider(VerificationProvider):
    """Mock NSIC single-point registration validity check."""

    name = "nsic_mock"

    def verify(self, identifier, context):
        if not identifier:
            return ProviderResult(
                VerificationStatus.NOT_FOUND,
                note="No NSIC certificate number could be read from the bidder's document.",
                provider_name=self.name,
            )
        key = identifier.strip().upper()
        record = mockdb.NSIC_DATABASE.get(key)
        if not record:
            return ProviderResult(
                VerificationStatus.NOT_FOUND,
                note=f"NSIC certificate {key} was not found in the mock NSIC dataset (MOCK DATA).",
                provider_name=self.name,
            )
        ok = record["status"] == "Valid"
        return ProviderResult(
            VerificationStatus.VERIFIED if ok else VerificationStatus.MISMATCH,
            data={"nsic_certificate_number": key, **record},
            note=f"Mock NSIC registry shows {key} status = '{record['status']}', valid upto {record.get('valid_upto')}.",
            provider_name=self.name,
        )


class DigiLockerVerificationProvider(VerificationProvider):
    """Mock DigiLocker document-authenticity check."""

    name = "digilocker_mock"

    def verify(self, identifier, context):
        if not identifier:
            return ProviderResult(
                VerificationStatus.NOT_FOUND,
                note="No DigiLocker document reference number could be read from the bidder's document.",
                provider_name=self.name,
            )
        key = identifier.strip().upper()
        record = mockdb.DIGILOCKER_DATABASE.get(key)
        if not record:
            return ProviderResult(
                VerificationStatus.NOT_FOUND,
                note=f"DigiLocker reference {key} was not found in the mock DigiLocker dataset (MOCK DATA).",
                provider_name=self.name,
            )
        ok = record["status"] == "Verified"
        return ProviderResult(
            VerificationStatus.VERIFIED if ok else VerificationStatus.MISMATCH,
            data={"document_reference_number": key, **record},
            note=f"Mock DigiLocker registry shows {key} status = '{record['status']}' (issued by {record.get('issued_by')}).",
            provider_name=self.name,
        )


class IncomeTaxVerificationProvider(VerificationProvider):
    """Mock Income Tax e-filing acknowledgement check."""

    name = "income_tax_mock"

    def verify(self, identifier, context):
        if not identifier:
            return ProviderResult(
                VerificationStatus.NOT_FOUND,
                note="No Income Tax acknowledgement number could be read from the bidder's document.",
                provider_name=self.name,
            )
        key = identifier.strip().upper()
        record = mockdb.INCOME_TAX_DATABASE.get(key)
        if not record:
            return ProviderResult(
                VerificationStatus.NOT_FOUND,
                note=f"Acknowledgement number {key} was not found in the mock Income Tax e-filing dataset (MOCK DATA).",
                provider_name=self.name,
            )
        ok = record["status"] == "Processed"
        return ProviderResult(
            VerificationStatus.VERIFIED if ok else VerificationStatus.MISMATCH,
            data={"acknowledgement_number": key, **record},
            note=f"Mock Income Tax e-filing registry shows {key} status = '{record['status']}' (AY {record.get('assessment_year')}).",
            provider_name=self.name,
        )


class BlacklistVerificationProvider(VerificationProvider):
    """
    Mock GeM blacklist/debarment check. Unlike the others, `identifier` here
    may be a PAN, a GSTIN, or a normalized company name - whichever the
    bidder's documents make available - and VERIFIED means "clean" (i.e. NOT
    found in the blacklist), while MISMATCH means "found in the blacklist".
    """

    name = "blacklist_mock"

    def verify(self, identifier, context):
        candidates = {
            str(v).strip().upper()
            for v in [identifier, context.get("company_name"), context.get("pan"), context.get("gstin")]
            if v
        }
        if not candidates:
            return ProviderResult(
                VerificationStatus.NOT_FOUND,
                note="No PAN, GSTIN, or company name was available to check against the blacklist.",
                provider_name=self.name,
            )
        hit = candidates & mockdb.BLACKLIST_DATABASE
        if hit:
            return ProviderResult(
                VerificationStatus.MISMATCH,
                data={"matched_on": sorted(hit)},
                note=f"Bidder identifier(s) {sorted(hit)} appear in the mock GeM blacklist dataset (MOCK DATA).",
                provider_name=self.name,
            )
        return ProviderResult(
            VerificationStatus.VERIFIED,
            data={"checked": sorted(candidates)},
            note="No match found in the mock GeM blacklist dataset.",
            provider_name=self.name,
        )


# Category (app.models.tender.RequirementCategory value) -> provider instance.
# Only categories with an external-registry-style check are listed here;
# threshold rules (turnover, make_in_india) and plain document-existence
# rules are handled directly by the compliance_engine without a provider.
PROVIDER_REGISTRY: Dict[str, VerificationProvider] = {
    "gst": GSTVerificationProvider(),
    "pan": PANVerificationProvider(),
    "identity": PANVerificationProvider(),
    "udyam_msme": UdyamVerificationProvider(),
    "company_registration": MCAVerificationProvider(),
    "bis": BISVerificationProvider(),
    "epfo": EPFOVerificationProvider(),
    "esic": ESICVerificationProvider(),
    "startup_dpiit": StartupDPIITVerificationProvider(),
    "nsic": NSICVerificationProvider(),
    "digilocker": DigiLockerVerificationProvider(),
    "income_tax": IncomeTaxVerificationProvider(),
    "blacklist_debarment": BlacklistVerificationProvider(),
}

# category -> the structured_fields key that holds the identifier to look up.
IDENTIFIER_FIELD_BY_CATEGORY: Dict[str, str] = {
    "gst": "gstin",
    "pan": "pan",
    "identity": "pan",
    "udyam_msme": "udyam_registration_number",
    "company_registration": "cin",
    "bis": "bis_license_number",
    "epfo": "epfo_establishment_id",
    "esic": "esic_registration_number",
    "startup_dpiit": "dpiit_certificate_number",
    "nsic": "nsic_certificate_number",
    "digilocker": "document_reference_number",
    "income_tax": "acknowledgement_number",
    "blacklist_debarment": "company_name",  # fallback identifier; provider also checks pan/gstin from context
}


def get_provider(category: str) -> Optional[VerificationProvider]:
    return PROVIDER_REGISTRY.get(category)
