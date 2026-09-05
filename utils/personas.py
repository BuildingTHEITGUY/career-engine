"""Dual-persona evaluation rubrics."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Persona:
    key: str
    label: str
    audience: str
    evaluates: tuple[str, ...]
    lenses: tuple[str, ...]
    lexicon: tuple[str, ...]
    weak_is_fatal: tuple[str, ...]


STUDENT = Persona(
    key="student",
    label="I am a student",
    audience="Early-career candidates, bootcamp grads, and career switchers",
    evaluates=(
        "Entry certifications and learning velocity",
        "Cloud basics (AWS / Azure / GCP fundamentals)",
        "Hands-on labs, homelabs, and portfolio evidence",
        "Security fundamentals and least-privilege thinking",
        "Linux, networking, Git, and scripting literacy",
    ),
    lenses=(
        "Prefer demonstrated labs over buzzwords.",
        "Reward GitHub, homelab, capture-the-flag, and internship evidence.",
        "Flag missing identity, networking, and security fundamentals.",
        "Do not punish lack of ITIL or board-level governance experience.",
        "Suggest the smallest next proof (lab, cert, or project) for each gap.",
    ),
    lexicon=(
        "aws",
        "azure",
        "gcp",
        "linux",
        "bash",
        "python",
        "git",
        "github",
        "networking",
        "tcp/ip",
        "dns",
        "dhcp",
        "vpn",
        "firewall",
        "iam",
        "s3",
        "ec2",
        "vpc",
        "active directory",
        "powershell",
        "docker",
        "kubernetes",
        "terraform",
        "ci/cd",
        "sql",
        "owasp",
        "mfa",
        "encryption",
        "least privilege",
        "incident response",
        "comptia",
        "security+",
        "cloud practitioner",
        "homelab",
        "wireshark",
        "ticketing",
        "servicenow",
        "help desk",
    ),
    weak_is_fatal=("responsible for", "helped with", "worked on", "participated in"),
)

PROFESSIONAL = Persona(
    key="professional",
    label="I am a Professional",
    audience="Mid-to-senior IT, GRC, service management, and delivery roles",
    evaluates=(
        "ITIL / ITSM practices and service outcomes",
        "Governance frameworks (COBIT, ISO 27001, NIST CSF, ISO 20000)",
        "Risk metrics, KRIs, residual vs inherent risk, and audit readiness",
        "IT project delivery, stakeholders, budget, and change control",
        "Vendor, SLA/OLA, and operating-model language",
    ),
    lenses=(
        "Score enterprise terminology as heavily as raw tools.",
        "Reward quantified service, risk, and delivery outcomes.",
        "Flag missing governance, risk, audit, or change-control language.",
        "Do not over-score homelab or classroom-only evidence.",
        "Rewrite gaps into board-safe, audit-safe CV phrasing.",
    ),
    lexicon=(
        "itil",
        "itsm",
        "incident management",
        "problem management",
        "change management",
        "service request",
        "sla",
        "ola",
        "cab",
        "pir",
        "cobit",
        "iso 27001",
        "iso 20000",
        "nist",
        "nist csf",
        "risk register",
        "kri",
        "residual risk",
        "inherent risk",
        "risk appetite",
        "audit",
        "sox",
        "gdpr",
        "vendor management",
        "raci",
        "stakeholder",
        "pmo",
        "kpi",
        "availability",
        "capacity",
        "disaster recovery",
        "business continuity",
        "bcp",
        "dr",
        "enterprise architecture",
        "governance",
        "control objective",
        "exception management",
        "third party risk",
        "service catalog",
    ),
    weak_is_fatal=("responsible for", "involved in", "tasked with", "assisted"),
)

PERSONAS: dict[str, Persona] = {
    STUDENT.key: STUDENT,
    PROFESSIONAL.key: PROFESSIONAL,
}


def get_persona(key: str) -> Persona:
    return PERSONAS.get(key, STUDENT)
