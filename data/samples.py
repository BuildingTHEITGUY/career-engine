"""Fictional samples for demos and LinkedIn before/after clips."""

from __future__ import annotations

STUDENT_CV = """
Amina Rahman
Junior Cloud & Support Candidate | Dubai
amina@email.example | github.com/amina-labs

SUMMARY
Recent IT graduate seeking a junior cloud or support role. Responsible for coursework,
labs, and a home lab. Team player with a passion for technology.

EDUCATION
B.Sc. Information Technology, 2025

EXPERIENCE
IT Support Intern — Campus Help Desk
- Responsible for helping students with password resets and Wi-Fi issues
- Worked on a ticketing tool and participated in weekly team meetings
- Helped image Windows laptops

PROJECTS
- Homelab: Ubuntu server, Docker, and a personal website
- AWS Academy labs: launched an EC2 instance and created an S3 bucket
- Python script that lists files in a folder

SKILLS
Windows, Microsoft Office, basic Linux, HTML, Python, customer service
"""

STUDENT_JD = """
Junior Cloud Support Associate
We are hiring a junior associate to support AWS workloads and first-line incidents.

Requirements:
- Hands-on AWS fundamentals (EC2, S3, IAM, VPC)
- Linux command line and basic networking (DNS, TCP/IP, VPN)
- Security fundamentals: MFA, least privilege, encryption at rest
- Git/GitHub evidence of labs or a homelab
- Ticketing experience (ServiceNow or similar)
- CompTIA Security+ or AWS Cloud Practitioner is a plus
- Clear written updates during incident response
"""

PROFESSIONAL_CV = """
Karim El-Sayed
IT Operations Lead | 8 years
karim@email.example

SUMMARY
Responsible for IT operations and project work across two business units.
Involved in audits and vendor calls. Strong communicator.

EXPERIENCE
IT Operations Lead — Regional Retail Group
- Responsible for incidents and changes
- Worked on a data-center migration project
- Helped the team during ISO discussions
- Tasked with vendor follow-ups and monthly reports
- Handled user access requests

IT Analyst — Managed Services Partner
- Participated in service desk improvements
- Involved in backup testing
- Assisted project managers with status updates

SKILLS
Windows Server, Active Directory, VMware, ServiceNow, ITIL Foundation,
project coordination, vendor management
"""

PROFESSIONAL_JD = """
IT Governance & Risk Analyst
Own the control narrative for IT services and report residual risk to the CISO office.

Must have:
- ITIL practices: incident, problem, change, and service catalog thinking
- Governance frameworks: COBIT, ISO 27001, NIST CSF
- Risk metrics: inherent vs residual risk, KRIs, risk register hygiene
- Audit evidence, exception management, and control owners (RACI)
- IT project delivery language: stakeholders, CAB, PIR, budget, and SLA/OLA
- Third-party / vendor risk awareness
- Ability to quantify availability, change success, and audit findings
"""

SAMPLES = {
    "student": {"cv": STUDENT_CV.strip(), "jd": STUDENT_JD.strip()},
    "professional": {"cv": PROFESSIONAL_CV.strip(), "jd": PROFESSIONAL_JD.strip()},
}
