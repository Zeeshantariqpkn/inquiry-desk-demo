"""Labeled questions, public facts and sample emails.

LABELED: each intent is one "real question" with several vendor wordings.
Used to (1) calibrate thresholds, (2) measure accuracy, (3) teach the
category classifier by example. Many wordings avoid the obvious keyword on
purpose, so the test checks meaning, not word matching.
"""

CATEGORIES = [
    "Eligibility & location", "Budget & pricing", "Schedule & deadlines",
    "Submission & format", "Platform & CMS", "Hosting & security",
    "Intranet", "Accessibility", "Content & migration", "Scope & support",
    "Contract & insurance",
]

# intent_id: (category, [wordings])
LABELED = {
    "E1": ("Eligibility & location", [
        "Can a company with a delivery team outside the United States perform the work remotely?",
        "Our engineers are based in India. Are offshore teams allowed to deliver this project?",
        "Is it acceptable for part of the development to be done by staff located overseas?",
        "Would a Canadian firm with developers in Pakistan be eligible to respond?",
        "Can the implementation and training be delivered entirely remotely from another country?",
    ]),
    "E2": ("Eligibility & location", [
        "Are subcontractors permitted on this project?",
        "May the prime contractor use a subcontractor for part of the work?",
        "Can we team with another firm and list them as a subcontractor?",
        "Is subcontracting any portion of the services allowed?",
    ]),
    "B1": ("Budget & pricing", [
        "Is there an estimated budget or not-to-exceed amount for this project?",
        "How much has the Commission set aside for this work?",
        "Is there a cap on the total contract value?",
        "Could you share the funding range so we can size our proposal?",
        "What dollar amount has been allocated to this RFP?",
        "Is there a ceiling on what the Commission is willing to spend?",
    ]),
    "B2": ("Budget & pricing", [
        "Should pricing be a fixed fee or hourly rates?",
        "Do you prefer a lump-sum price or a time-and-materials proposal?",
        "Can we propose hourly billing instead of a fixed price?",
        "What pricing model should respondents use on the cost form?",
    ]),
    "S1": ("Schedule & deadlines", [
        "What is the current proposal due date?",
        "Has the submission deadline been extended?",
        "Is the due date still November 20 or has it moved?",
        "When are proposals now due after the extension?",
        "Could the Commission give respondents more time to submit?",
    ]),
    "S2": ("Schedule & deadlines", [
        "When will answers to vendor questions be published?",
        "When can we expect the addendum with responses to our questions?",
        "We sent questions last week and have not heard back. When will they be answered?",
        "Is there a date for releasing the Q&A?",
    ]),
    "S3": ("Schedule & deadlines", [
        "What is the expected start date and go-live date for the new website?",
        "When does the Commission want the new site launched?",
        "Is there a target launch timeline for the website and intranet?",
        "How long is the project expected to take from award to launch?",
    ]),
    "U1": ("Submission & format", [
        "Can proposals be submitted on paper, or only electronically?",
        "Do you need printed copies of the proposal?",
        "Should we mail a hard copy or send a PDF by email?",
        "Where and how should the response be delivered?",
    ]),
    "U2": ("Submission & format", [
        "Is there a page limit for the technical proposal?",
        "How long can our response be?",
        "Are there font size or formatting rules for the proposal?",
        "Is there a maximum number of pages we must stay within?",
    ]),
    "P1": ("Platform & CMS", [
        "Does the Commission require a specific content management system?",
        "Must the new website stay on the current Sitefinity platform?",
        "Is there a preferred CMS such as WordPress or Drupal?",
        "Are we free to recommend whichever platform we think is best for managing the site?",
        "Has the Commission already chosen the software the new site will be built on?",
    ]),
    "H1": ("Hosting & security", [
        "Will the selected vendor host the site, or will the Commission host it?",
        "Who is responsible for hosting after launch?",
        "Should our proposal include hosting, or does the Commission run its own servers?",
        "Is vendor-managed cloud hosting acceptable?",
    ]),
    "H2": ("Hosting & security", [
        "Must Commission data be stored in the United States?",
        "Are there data residency requirements for the hosting environment?",
        "Can the site be hosted in a data center outside the US?",
        "Where must backups and Commission data be kept?",
    ]),
    "H3": ("Hosting & security", [
        "Does the vendor need a SOC 2 report or other security certification?",
        "What security standards must the solution meet?",
        "Will a penetration test be required before launch?",
        "Are there cybersecurity requirements the vendor must certify to?",
    ]),
    "I1": ("Intranet", [
        "What platform is the current intranet built on?",
        "Is the existing intranet running on SharePoint?",
        "Should the new intranet be built in Microsoft 365?",
        "What system do employees use for the internal site today?",
    ]),
    "I2": ("Intranet", [
        "How many employees use the intranet?",
        "How many staff will need to log in to the internal site?",
        "Should the intranet use single sign-on with employee accounts?",
        "What is the number of intranet users we should plan for?",
    ]),
    "A1": ("Accessibility", [
        "What accessibility standard must the website meet?",
        "Is WCAG 2.1 AA conformance required?",
        "Does the site need to comply with Section 508?",
        "Which level of accessibility compliance is expected for the public site and intranet?",
    ]),
    "A2": ("Accessibility", [
        "Is remediation of existing PDF documents for accessibility in scope?",
        "Do we need to make the current PDFs accessible?",
        "Should the vendor fix accessibility issues in documents already on the site?",
        "Are accessible versions of existing documents part of the work?",
    ]),
    "C1": ("Content & migration", [
        "Approximately how many pages and documents need to be migrated?",
        "What is the page count of the current website?",
        "How large is the existing content library we would move to the new site?",
        "How many PDF files are on the current site?",
    ]),
    "C2": ("Content & migration", [
        "Will Commission staff write the content, or is copywriting in scope?",
        "Is content rewriting part of the vendor's work?",
        "Who is responsible for creating new text for the site?",
        "Should we include content writing services in our proposal?",
    ]),
    "X1": ("Scope & support", [
        "Is there an incumbent vendor for the current website?",
        "Who built and maintains the existing site?",
        "Is the current website vendor allowed to respond?",
        "Which company supports the website today?",
    ]),
    "X2": ("Scope & support", [
        "How many years of ongoing support and maintenance should we price?",
        "Is post-launch maintenance part of this contract?",
        "Should the proposal include support after the site goes live?",
        "What level of ongoing support is expected once the project is complete?",
    ]),
    "K1": ("Contract & insurance", [
        "What insurance coverage is required of the contractor?",
        "What are the minimum insurance limits for this contract?",
        "Do we need cyber liability insurance?",
        "Which certificates of insurance must the vendor provide?",
    ]),
    "K2": ("Contract & insurance", [
        "Will a performance bond be required?",
        "Does the selected vendor need to post a bond?",
        "Is a surety bond part of the contract requirements?",
        "Must the contractor provide a performance or payment bond?",
    ]),
    "K3": ("Contract & insurance", [
        "Can respondents propose changes to the contract terms?",
        "Is the form contract negotiable?",
        "May we submit exceptions to the master contract?",
        "Should exceptions to the contract be included with the proposal?",
    ]),
}

# Public facts only (RFP 19-2026 notice and Addenda No. 1 and 2).
# Each fact lists the intents it answers, so drafts are cited, never invented.
KB = [
    {"id": "add1-a1", "answers": ["E1"], "cite": "Addendum No. 1, A#1",
     "text": "Executive Orders Nos. 2019-12D and 2022-02D prohibit the expenditure of public funds for services performed or data storage located outside of the United States. Respondents must disclose all locations where services would be performed and where Commission data would be stored on Appendix F (Affirmation and Disclosure Form). A waiver from Ohio DAS would be required for any location outside the United States, and the Commission considers such a waiver highly unlikely."},
    {"id": "add1-data", "answers": ["H2"], "cite": "Addendum No. 1, A#1 · Appendix F",
     "text": "Yes. Executive Orders Nos. 2019-12D and 2022-02D prohibit the expenditure of public funds for data storage located outside of the United States. All data storage locations must be disclosed on Appendix F (Affirmation and Disclosure Form)."},
    {"id": "add2-due", "answers": ["S1"], "cite": "Addendum No. 2",
     "text": "The proposal due date has been extended to 5:00 P.M. (Eastern Time) on December 11, 2026."},
    {"id": "add2-answers", "answers": ["S2"], "cite": "Addendum No. 2",
     "text": "The Commission expects to issue an addendum answering all questions received during the inquiry period on or before November 20, 2026."},
    {"id": "notice-submit", "answers": ["U1"], "cite": "Notice to Respondents, RFP No. 19-2026",
     "text": "Proposals must be submitted as one softcopy in PDF format by email to purchasing@ohioturnpike.org. Paper copies will be considered non-responsive."},
]

# Sample inbox: (days after Oct 13, hour, firm, contact, subject, [question texts])
FIRMS = [
    ("Lakeshore Digital Group", "Megan Carter"), ("Buckeye Web Partners", "Daniel Ortiz"),
    ("Northcoast Interactive", "Priya Nair"), ("Summit Civic Tech", "Robert Hale"),
    ("Meridian Software Ltd.", "Ahmed Raza"), ("BrightPath Solutions", "Laura Kim"),
    ("Keystone Creative", "Tom Becker"), ("Ironbridge Systems", "Sandra Lopez"),
    ("Harbor UX Studio", "Kevin Walsh"), ("Pinecrest Consulting", "Emily Novak"),
    ("Cuyahoga Design Co.", "Marcus Bell"), ("Atlas GovTech", "Jennifer Park"),
    ("Riverbend Digital", "Chris Allen"), ("Granite Peak Web", "Olivia Stone"),
]

SEED = [
    (0, 10, 4, "Offshore delivery question", ["Our engineers are based in India. Are offshore teams allowed to deliver this project?"]),
    (1, 11, 5, "Eligibility", ["Would a Canadian firm with developers in Pakistan be eligible to respond?"]),
    (2, 9, 1, "Budget for RFP 19-2026", ["Is there an estimated budget or not-to-exceed amount for this project?"]),
    (3, 14, 6, "Question on funding", ["How much has the Commission set aside for this work?"]),
    (4, 10, 9, "Three questions", ["1. Is there a cap on the total contract value?", "2. Must the new website stay on the current Sitefinity platform?", "3. Is WCAG 2.1 AA conformance required?"]),
    (4, 15, 2, "CMS preference", ["Is there a preferred CMS such as WordPress or Drupal?"]),
    (5, 9, 11, "Platform", ["Are we free to recommend whichever platform we think is best for managing the site?"]),
    (5, 13, 3, "Hosting", ["Will the selected vendor host the site, or will the Commission host it?"]),
    (6, 10, 7, "Budget and hosting", ["Could you share the funding range so we can size our proposal?", "Also, who is responsible for hosting after launch?"]),
    (7, 9, 0, "Due date", ["Is the due date still November 20 or has it moved?"]),
    (7, 16, 12, "Submission format", ["Should we mail a hard copy or send a PDF by email?"]),
    (8, 11, 8, "Accessibility", ["Which level of accessibility compliance is expected for the public site and intranet?"]),
    (8, 14, 13, "PDF remediation", ["Do we need to make the current PDFs accessible?"]),
    (9, 10, 10, "Content migration", ["Approximately how many pages and documents need to be migrated?"]),
    (9, 15, 4, "Intranet", ["Is the existing intranet running on SharePoint?", "How many employees use the intranet?"]),
    (10, 9, 6, "Ceiling on spend", ["Is there a ceiling on what the Commission is willing to spend?"]),
    (10, 13, 1, "Incumbent", ["Is there an incumbent vendor for the current website?"]),
    (11, 10, 5, "Support term", ["How many years of ongoing support and maintenance should we price?"]),
    (11, 14, 3, "Insurance", ["What insurance coverage is required of the contractor?"]),
    (12, 9, 2, "Answers timing", ["When will answers to vendor questions be published?"]),
    (12, 15, 9, "Remote delivery", ["Can the implementation and training be delivered entirely remotely from another country?"]),
    (13, 10, 7, "Performance bond", ["Will a performance bond be required?"]),
    (13, 16, 11, "Budget", ["What dollar amount has been allocated to this RFP?"]),
    (14, 11, 0, "Data location", ["Must Commission data be stored in the United States?"]),
    (14, 15, 12, "Page limit", ["Is there a page limit for the technical proposal?"]),
    (16, 10, 13, "Late question: budget", ["Is there a budget for this project?"]),
    (17, 11, 8, "Late question: due date", ["When are proposals now due after the extension?"]),
    (18, 14, 10, "Late: offshore", ["Is it acceptable for part of the development to be done by staff located overseas?"]),
]
