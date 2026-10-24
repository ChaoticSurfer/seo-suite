"""Google rich-result requirements for JSON-LD, as pure data + a pure validator.

Source: developers.google.com/search/docs/appearance/structured-data/search-gallery
(and each feature's page). `required_any` means at least one of the listed
properties must be present; `recommended_any` is the same for a recommendation.
Re-check the gallery when Google announces changes.
"""
from __future__ import annotations

from seo_lib import Finding

TYPE_RULES: dict[str, dict] = {
    "Article": {"recommended": ["headline", "image", "datePublished", "dateModified", "author"]},
    "NewsArticle": {"recommended": ["headline", "image", "datePublished", "dateModified", "author"]},
    "BlogPosting": {"recommended": ["headline", "image", "datePublished", "dateModified", "author"]},
    "Product": {
        "required": ["name"],
        "required_any": [["offers", "review", "aggregateRating"]],
        "recommended": ["image", "description", "sku", "brand", "offers"],
        "recommended_any": [["gtin", "gtin8", "gtin12", "gtin13", "gtin14"]],
    },
    "Offer": {
        "required_any": [["price", "priceSpecification"]],
        "recommended": ["priceCurrency", "availability", "url", "itemCondition", "shippingDetails", "hasMerchantReturnPolicy"],
    },
    "AggregateRating": {"required": ["ratingValue"], "required_any": [["ratingCount", "reviewCount"]]},
    "Review": {"required": ["author", "reviewRating"], "recommended": ["datePublished"]},
    "BreadcrumbList": {"required": ["itemListElement"]},  # needs ≥2 ListItems (checked below)
    "ListItem": {"required": ["position"]},  # name/item rules differ per list (a carousel item needs only url), so BreadcrumbList checks its crumbs below
    # productGroupID may instead come as inProductGroupWithID on every variant.
    "ProductGroup": {"required": ["name"], "recommended": ["productGroupID", "variesBy", "hasVariant", "brand", "url"]},
    "OfferShippingDetails": {"required": ["shippingDestination", "shippingRate", "deliveryTime"]},
    "MerchantReturnPolicy": {"required": ["applicableCountry", "returnPolicyCategory"],
                             "recommended": ["merchantReturnDays", "returnFees", "returnMethod"]},
    "AggregateOffer": {"required": ["lowPrice", "priceCurrency"], "recommended": ["highPrice", "offerCount"]},
    "Organization": {"recommended": ["name", "url", "logo", "sameAs", "contactPoint", "address"]},
    "LocalBusiness": {
        "required": ["name", "address"],
        "recommended": ["url", "telephone", "geo", "openingHoursSpecification", "priceRange", "image", "aggregateRating"],
    },
    "Event": {
        "required": ["name", "startDate", "location", "location.address"],  # physical events only since June 2025
        "recommended": ["endDate", "eventStatus", "eventAttendanceMode", "image", "description", "offers", "organizer", "performer"],
    },
    "JobPosting": {
        "required": ["title", "description", "datePosted", "hiringOrganization"],
        "required_any": [["jobLocation", "applicantLocationRequirements"]],
        "recommended": ["validThrough", "baseSalary", "employmentType", "identifier", "directApply", "jobLocationType"],
    },
    "VideoObject": {
        "required": ["name", "thumbnailUrl", "uploadDate"],
        "recommended": ["description", "contentUrl", "embedUrl", "duration", "expires"],
    },
    "Recipe": {
        "required": ["name", "image"],
        "recommended": ["author", "datePublished", "description", "recipeIngredient", "recipeInstructions",
                        "totalTime", "recipeYield", "nutrition", "aggregateRating", "video"],
    },
    "SoftwareApplication": {
        "required": ["name", "offers"],
        "required_any": [["aggregateRating", "review"]],
        "recommended": ["applicationCategory", "operatingSystem"],
    },
    # Dataset: description must be 50–5000 chars; the markup feeds Dataset Search only.
    "Dataset": {"required": ["name", "description"], "recommended": ["url", "license", "creator", "distribution"]},
    "ProfilePage": {"required": ["mainEntity"], "recommended": ["dateCreated", "dateModified"]},
    "DiscussionForumPosting": {
        "required": ["author", "datePublished"],
        "required_any": [["text", "image", "video"]],
        "recommended": ["headline", "url", "comment", "interactionStatistic"],
    },
    "QAPage": {"required": ["mainEntity"]},
    "Question": {"required": ["name"], "recommended": ["acceptedAnswer", "suggestedAnswer", "answerCount"]},
    "WebSite": {"recommended": ["name", "url", "alternateName"]},
    "Person": {"recommended": ["name", "url", "sameAs", "jobTitle", "image"]},
}
TYPE_RULES["SoftwareApplication"]["aliases"] = ["MobileApplication", "WebApplication"]
TYPE_RULES["Organization"]["aliases"] = ["EducationalOrganization"]  # an Organization (and CivicStructure), not a LocalBusiness

# LocalBusiness subtypes are numerous; treat any of these as LocalBusiness.
LOCAL_BUSINESS_SUBTYPES = {
    "Restaurant", "Store", "Dentist", "MedicalClinic", "Hotel", "AutoRepair", "LegalService", "RealEstateAgent",
    "HealthAndBeautyBusiness", "HomeAndConstructionBusiness", "ProfessionalService", "FinancialService",
    "FoodEstablishment", "LodgingBusiness", "SportsActivityLocation",
}

# Types that validate fine but no longer earn (or rarely earn) a Google rich result.
LIMITED_OR_RETIRED = {
    "FAQPage": "FAQ rich results stopped showing in Google on 2026-05-07. Markup is harmless and still helps other engines parse Q&A; expect no Google rich result.",
    "HowTo": "HowTo rich results were removed from Google in 2023.",
    "ClaimReview": "Fact-check rich results were phased out in 2025.",
    "Book": "Book actions were phased out in 2025.",
    "Course": "Course info rich results were removed on 2025-09-09. If this Course sits in an ItemList for the Course list carousel, that feature is still supported.",
    "EstimatedSalary": "Removed 2025-09-09.",
    "LearningResource": "Learning video rich results were removed 2025-09-09.",
    "SpecialAnnouncement": "Removed 2025-09-09.",
    "Vehicle": "Vehicle listing rich results were removed 2025-09-09.",
    "Car": "Vehicle listing rich results were removed 2025-09-09.",
    "SearchAction": "The sitelinks search box was removed on 2024-11-21; WebSite potentialAction SearchAction earns nothing.",
}


def iter_typed_nodes(node, path: str = "$"):
    """Yield (path, dict) for every JSON-LD object that declares an @type, including inside @graph."""
    if isinstance(node, list):
        for i, item in enumerate(node):
            yield from iter_typed_nodes(item, f"{path}[{i}]")
    elif isinstance(node, dict):
        if "@type" in node:
            yield path, node
        for key, value in node.items():
            if isinstance(value, (dict, list)):
                yield from iter_typed_nodes(value, f"{path}.{key}")


def node_types(node: dict) -> list[str]:
    raw = node.get("@type", [])
    return [t.rsplit("/", 1)[-1] for t in (raw if isinstance(raw, list) else [raw]) if isinstance(t, str)]


def _rule_for(type_name: str) -> tuple[str, dict] | None:
    if type_name in TYPE_RULES:
        return type_name, TYPE_RULES[type_name]
    if type_name in LOCAL_BUSINESS_SUBTYPES:
        return "LocalBusiness", TYPE_RULES["LocalBusiness"]
    for name, rule in TYPE_RULES.items():
        if type_name in rule.get("aliases", []):
            return name, rule
    return None


def _present(node: dict, prop: str) -> bool:
    """True if `prop` (dotted for nesting, e.g. 'location.address') has a value; lists match if any item does."""
    head, _, rest = prop.partition(".")
    value = node.get(head)
    if value in (None, "", [], {}):
        return False
    if not rest:
        return True
    items = value if isinstance(value, list) else [value]
    return any(isinstance(item, dict) and _present(item, rest) for item in items)


def validate_json_ld(blocks: list) -> tuple[list[str], list[Finding]]:
    """Return (types found, findings) for a page's parsed JSON-LD blocks."""
    types_found: list[str] = []
    findings: list[Finding] = []
    for path, node in iter_typed_nodes(blocks):
        for type_name in node_types(node):
            types_found.append(type_name)
            if type_name in LIMITED_OR_RETIRED:
                findings.append(Finding("schema-limited-type", "info", f"{type_name}: {LIMITED_OR_RETIRED[type_name]}", path))
            matched = _rule_for(type_name)
            if not matched:
                continue
            rule_name, rule = matched
            for prop in rule.get("required", []):
                if not _present(node, prop):
                    findings.append(Finding("schema-missing-required", "high", f"{type_name} is missing required '{prop}' (Google {rule_name} rules)", path))
            for group in rule.get("required_any", []):
                if not any(_present(node, p) for p in group):
                    findings.append(Finding("schema-missing-required", "high", f"{type_name} needs one of {group}", path))
            missing_recommended = [p for p in rule.get("recommended", []) if not _present(node, p)]
            missing_recommended += [" | ".join(group) for group in rule.get("recommended_any", [])
                                    if not any(_present(node, p) for p in group)]
            if missing_recommended:
                findings.append(Finding("schema-missing-recommended", "low", f"{type_name} lacks recommended {missing_recommended}", path))
    own_business = {"Organization", "LocalBusiness"} | LOCAL_BUSINESS_SUBTYPES | set(TYPE_RULES["Organization"]["aliases"])
    for path, node in iter_typed_nodes(blocks):
        types = set(node_types(node))
        if types & own_business and (node.get("aggregateRating") or node.get("review")):
            findings.append(Finding("schema-self-serving-review", "medium",
                                    "Reviews/ratings on your own Organization/LocalBusiness are self-serving and ineligible for review snippets", path))
        items = node.get("itemListElement")
        if "BreadcrumbList" in node_types(node) and isinstance(items, list):
            if len(items) < 2:
                findings.append(Finding("schema-breadcrumb-short", "medium", "BreadcrumbList needs at least 2 ListItems", path))
            for i, crumb in enumerate(items):
                if not isinstance(crumb, dict):
                    continue
                crumb_path = f"{path}.itemListElement[{i}]"
                if not (_present(crumb, "name") or _present(crumb, "item.name")):  # name may come from an item Thing
                    findings.append(Finding("schema-missing-required", "high", "BreadcrumbList crumb is missing required 'name' (or item.name)", crumb_path))
                if i < len(items) - 1 and not _present(crumb, "item"):
                    findings.append(Finding("schema-missing-required", "high", "BreadcrumbList crumb is missing required 'item' (only the last crumb may omit it)", crumb_path))
    for i, block in enumerate(blocks):
        for top in block if isinstance(block, list) else [block]:
            if isinstance(top, dict) and "@context" not in top:
                findings.append(Finding("schema-no-context", "medium", "JSON-LD object has no @context; parsers may ignore it", f"block {i}"))
    return types_found, findings
