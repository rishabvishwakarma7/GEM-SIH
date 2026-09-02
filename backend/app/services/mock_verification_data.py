"""
Dummy/mock "government registry" datasets for the Day-4 verification engine.

*** THESE ARE NOT REAL GOVERNMENT RECORDS. ***
Every dataset below is hand-authored fictional data for hackathon demo and
testing purposes only. Nothing here was scraped, copied, or derived from any
real GST Network / Udyam / MCA21 / BIS CareCert / GeM system, and no code in
this project ever claims otherwise (see VerificationResult.is_mock, always
True, and the `note` string every provider attaches to its result).

Swapping in a real API later means writing a new VerificationProvider
subclass (see verification_providers.py) that calls the real endpoint instead
of looking things up in these dicts — nothing else in the engine changes.

Design of the dataset (deliberately covers every demo/test scenario):
  - "COMPLIANT TRADERS PRIVATE LIMITED"  -> clean across GST/PAN/MCA -> COMPLIANT bidder
  - "RELIABLE ENGINEERING WORKS"          -> clean GST/PAN/Udyam, no MCA record -> mostly COMPLIANT
  - "STRUGGLING SUPPLIES LLP"             -> GST Cancelled, MCA Struck Off -> NON_COMPLIANT
  - "SUSPENDED SYSTEMS PVT LTD"           -> GST Suspended -> NON_COMPLIANT
  - "BLACKLISTED VENDORS INDIA PVT LTD"   -> present in the blacklist dataset -> NON_COMPLIANT
  - any identifier NOT in these dicts     -> NOT_FOUND -> NEEDS_REVIEW
"""

# GSTIN -> record. "status" must be exactly "Active" to pass the GST rule.
# "return_filing_status" is informational (surfaced in the verification note /
# provider data) and does NOT itself gate the deterministic GST rule below -
# only "status" does, to avoid silently changing existing demo scenarios.
GST_DATABASE = {
    "33AAACC1206D1ZM": {
        "legal_name": "COMPLIANT TRADERS PRIVATE LIMITED",
        "status": "Active",
        "registration_date": "2019-07-01",
        "return_filing_status": "Filed",
        "last_return_period": "2026-07",
    },
    "27AAAPL2356Q1Z7": {
        "legal_name": "RELIABLE ENGINEERING WORKS",
        "status": "Active",
        "registration_date": "2020-01-15",
        "return_filing_status": "Filed",
        "last_return_period": "2026-07",
    },
    "07AABCU9603R1ZM": {
        "legal_name": "STRUGGLING SUPPLIES LLP",
        "status": "Cancelled",
        "registration_date": "2018-03-10",
        "return_filing_status": "Not Filed",
        "last_return_period": "2023-11",
    },
    "29AAECS1234F1Z5": {
        "legal_name": "SUSPENDED SYSTEMS PVT LTD",
        "status": "Suspended",
        "registration_date": "2021-06-20",
        "return_filing_status": "Not Filed",
        "last_return_period": "2025-02",
    },
    "19AABCB0001Z1ZQ": {
        "legal_name": "BLACKLISTED VENDORS INDIA PVT LTD",
        "status": "Active",
        "registration_date": "2017-11-05",
        "return_filing_status": "Filed",
        "last_return_period": "2026-06",
    },
}

# EPFO establishment ID -> record.
EPFO_DATABASE = {
    "TNCHE1234567000": {
        "company_name": "COMPLIANT TRADERS PRIVATE LIMITED",
        "status": "Active",
        "registration_date": "2019-08-01",
    },
    "MHPUN0987654000": {
        "company_name": "RELIABLE ENGINEERING WORKS",
        "status": "Active",
        "registration_date": "2020-02-15",
    },
    "TNCHE7654321000": {
        "company_name": "STRUGGLING SUPPLIES LLP",
        "status": "Inactive",
        "registration_date": "2018-04-10",
    },
}

# ESIC registration number -> record.
ESIC_DATABASE = {
    "33000123450000999": {
        "company_name": "COMPLIANT TRADERS PRIVATE LIMITED",
        "status": "Active",
        "registration_date": "2019-08-05",
    },
    "27000987650000111": {
        "company_name": "RELIABLE ENGINEERING WORKS",
        "status": "Active",
        "registration_date": "2020-02-20",
    },
}

# DPIIT Startup India recognition certificate number -> record.
STARTUP_DPIIT_DATABASE = {
    "DIPP12345": {
        "company_name": "RELIABLE ENGINEERING WORKS",
        "status": "Recognized",
        "registration_date": "2021-03-01",
    },
}

# NSIC single-point registration certificate number -> record.
NSIC_DATABASE = {
    "NSIC/CRM/2022/00123": {
        "company_name": "RELIABLE ENGINEERING WORKS",
        "status": "Valid",
        "valid_upto": "2027-03-31",
    },
    "NSIC/CRM/2019/00045": {
        "company_name": "STRUGGLING SUPPLIES LLP",
        "status": "Expired",
        "valid_upto": "2022-03-31",
    },
}

# DigiLocker issued-document reference number -> record.
DIGILOCKER_DATABASE = {
    "DL-2023-AB12CD34": {
        "company_name": "COMPLIANT TRADERS PRIVATE LIMITED",
        "status": "Verified",
        "issued_by": "DigiLocker - CBDT",
    },
}

# Income Tax e-filing acknowledgement number -> record.
INCOME_TAX_DATABASE = {
    "123456789012345": {
        "company_name": "COMPLIANT TRADERS PRIVATE LIMITED",
        "status": "Processed",
        "assessment_year": "2025-26",
    },
    "234567890123456": {
        "company_name": "RELIABLE ENGINEERING WORKS",
        "status": "Processed",
        "assessment_year": "2025-26",
    },
}

# PAN -> record. Existence + name is what's checked; a PAN not on file is NOT_FOUND.
PAN_DATABASE = {
    "AAACC1206D": {"legal_name": "COMPLIANT TRADERS PRIVATE LIMITED", "status": "Valid"},
    "AAAPL2356Q": {"legal_name": "RELIABLE ENGINEERING WORKS", "status": "Valid"},
    "AABCU9603R": {"legal_name": "STRUGGLING SUPPLIES LLP", "status": "Valid"},
    "AAECS1234F": {"legal_name": "SUSPENDED SYSTEMS PVT LTD", "status": "Valid"},
    "AABCB0001Z": {"legal_name": "BLACKLISTED VENDORS INDIA PVT LTD", "status": "Valid"},
}

# Udyam registration number -> record.
UDYAM_DATABASE = {
    "UDYAM-TN-03-0012345": {
        "enterprise_category": "Small",
        "status": "Active",
        "registration_date": "2021-02-11",
    },
    "UDYAM-MH-05-0067890": {
        "enterprise_category": "Micro",
        "status": "Active",
        "registration_date": "2022-05-19",
    },
}

# CIN -> record (mock MCA21 company master data).
MCA_DATABASE = {
    "U29100TN2015PTC098765": {
        "company_name": "COMPLIANT TRADERS PRIVATE LIMITED",
        "status": "Active",
        "registration_date": "2015-09-14",
    },
    "U27100MH2010PLC112233": {
        "company_name": "STRUGGLING SUPPLIES LLP",
        "status": "Struck Off",
        "registration_date": "2010-04-02",
    },
}

# BIS license/CML number -> record.
BIS_DATABASE = {
    "CML/O/12345678": {
        "status": "Valid",
        "valid_upto": "2027-03-31",
        "product": "IS 16046 - LED Luminaires",
    },
    "CML/O/00000000": {
        "status": "Expired",
        "valid_upto": "2023-01-01",
        "product": "IS 302 - Household Appliances",
    },
}

# Configured GeM blacklist / debarment dataset. Any of PAN, GSTIN, or a
# normalized company name landing in this set fails the blacklist check.
BLACKLIST_DATABASE = {
    "AABCB0001Z",                       # PAN
    "19AABCB0001Z1ZQ",                  # GSTIN
    "BLACKLISTED VENDORS INDIA PVT LTD",  # normalized company name
}
