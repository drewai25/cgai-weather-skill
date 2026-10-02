To: Tunde Mottley
Subject: Three corrections to the nine-standards sheet
Status: DRAFT -- not yet sent

Not a sign-off request. These are figures in the sheet that are wrong and
are heading to Roger.

---

Tunde,

Three corrections to the sheet before it goes further. No action needed from
you beyond changing them; I'll have the tables shortly.

**The irradiance coverage figures are wrong in kind, not just in value.** The
sheet reads "coverage runs 83-90% May to September but 42-45% in March and
November to December", which describes a season. Measured from the data, it
is two instrument outages:

    2024-03-13 .. 2024-05-02     50.5 days
    2024-10-14 .. 2025-04-06    173.1 days

November 2025 is 89.7%, December 2025 is 89.9%, March 2026 is 89.0% -- the
same calendar months are fine the following year. Hourly completeness at the
90% bar across the frozen window is 16,435 of 23,976 hours, 68.5%.

**Standard 7 is better than stated.** The sheet says "Free tier is CC BY 4.0
non-commercial." Open-Meteo's data licence is CC BY 4.0 and explicitly
permits commercial use with attribution; it is the free API tier's terms of
service that restrict access to non-commercial use under 10,000 calls a day.
Deployment needs a paid tier for access, not for rights to the data.

**Standard 1 cannot close on that sentence.** It reads "measured archive
depths match the published documentation." Open-Meteo lists ECMWF IFS HRES
9 km on two pages and the API rejects it on both endpoints. The standard can
still close; not on that wording.

**And the Observatory licence is unresolved in a new way.** The dataset's own
attribute reads CC0-1.0. Rowan's email of 1 October says CC BY. The portal
states neither. I have asked him which is authoritative.

Andrew
