"""Hand-maintained synonym groups used to canonicalise column tokens.

Column names differ between systems in a small number of predictable
ways: an abbreviation (``qty``), a domain word (``premium`` vs ``fee``),
or a different noun for the same person (``employee`` vs ``staff``). Each
group below collapses to its first member, so ``Policy_No`` and
``PolicyNumber`` both reduce to ``policy number``.

Add a row to extend the vocabulary; nothing else needs to change.
"""

from __future__ import annotations

SYNONYM_GROUPS: tuple[tuple[str, ...], ...] = (
    ("number", "no", "num", "nbr", "numb"),
    ("identifier", "id", "code", "ref", "reference", "key"),
    ("amount", "amt", "total", "sum", "value"),
    ("price", "premium", "fee", "charge", "cost", "rate"),
    ("date", "dt", "day", "datetime", "timestamp", "time"),
    ("person", "employee", "emp", "staff", "worker", "member", "user", "individual"),
    ("customer", "client", "cust", "buyer", "purchaser"),
    ("recipient", "receiver", "consignee", "addressee"),
    ("name", "fullname", "label"),
    ("first", "given", "fore"),
    ("last", "surname", "family"),
    ("phone", "tel", "telephone", "mobile", "cell", "msisdn"),
    ("email", "mail", "emailaddress"),
    ("address", "addr", "street"),
    ("city", "town", "locality"),
    ("region", "state", "province", "county"),
    ("postcode", "zip", "zipcode", "postal", "postalcode", "pincode"),
    ("country", "nation"),
    ("quantity", "qty", "count", "units", "unit"),
    (
        "description",
        "desc",
        "details",
        "detail",
        "notes",
        "note",
        "comment",
        "remark",
        "narrative",
    ),
    ("account", "acct", "acc"),
    ("transaction", "txn", "trx", "trans"),
    ("status", "stage", "phase"),
    ("created", "creation", "opened", "issued"),
    ("updated", "modified", "changed"),
    ("plan", "tier", "package", "scheme", "product", "offering"),
    ("type", "kind", "category", "class", "classification"),
    ("policy", "contract", "agreement"),
    ("salary", "wage", "pay", "compensation", "remuneration"),
    ("department", "dept", "division", "team", "unit"),
    ("role", "job", "position", "designation", "title", "occupation"),
    ("gender", "sex"),
    ("birth", "dob", "born", "birthdate", "birthday"),
    ("company", "organisation", "organization", "org", "employer", "vendor", "supplier"),
    ("currency", "ccy"),
    ("active", "enabled", "live"),
    ("start", "begin", "commence", "effective"),
    ("end", "finish", "expiry", "expiration", "termination"),
    ("latitude", "lat"),
    ("longitude", "lng", "lon"),
    ("invoice", "bill"),
    ("order", "purchase", "purchased", "bought"),
    ("hired", "hire", "joining", "joined", "onboarded"),
    ("shipped", "ship", "shipping", "dispatch", "dispatched", "despatch"),
    ("delivery", "delivered", "deliver", "dropoff"),
    ("destination", "dest"),
    ("weight", "mass"),
    ("discount", "rebate", "reduction"),
    ("tax", "vat", "gst"),
)

# token -> canonical token. Built once at import.
CANONICAL: dict[str, str] = {member: group[0] for group in SYNONYM_GROUPS for member in group}

# Compound names whose parts mean something else on their own: a postal
# "code" is not an identifier, and a "full name" is just a name. Keys are
# sequences of already-canonicalised tokens, so ("postcode", "identifier")
# covers "PostalCode", "zip_code" and "Post Code" alike.
PHRASES: dict[tuple[str, ...], str] = {
    ("postcode", "identifier"): "postcode",
    ("area", "identifier"): "areacode",
    ("country", "identifier"): "countrycode",
    ("dial", "identifier"): "dialcode",
    ("phone", "number"): "phone",
    ("email", "identifier"): "email",
    ("email", "address"): "email",
    ("full", "name"): "name",
    ("first", "name"): "firstname",
    ("last", "name"): "lastname",
    ("birth", "date"): "birth",
    ("date", "birth"): "birth",
    ("street", "address"): "address",
}

MAX_PHRASE_LENGTH = max(len(phrase) for phrase in PHRASES)

# Words that carry no matching signal on their own.
STOPWORDS: frozenset[str] = frozenset(
    {"the", "a", "an", "of", "for", "and", "col", "on", "at", "in", "by", "with"}
)

# Tokens whose trailing "s" is part of the word, not a plural marker.
NON_PLURAL: frozenset[str] = frozenset(
    {"status", "address", "class", "gross", "business", "series", "always"}
)
