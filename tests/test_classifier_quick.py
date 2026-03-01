"""Quick validation of the archetype classifier rule-based fast-path."""

from src.serving.archetype_classifier import classify_fast, ArchetypeClassifier


def test_esploratore_italian():
    r = classify_fast("Datemi qualcosa di veloce, economico")
    assert r is not None
    assert r.archetype == "Esploratore Galattico"
    assert r.method == "rules"


def test_esploratore_english():
    r = classify_fast("I want something quick and cheap, anything edible will do")
    assert r is not None
    assert r.archetype == "Esploratore Galattico"


def test_astrobarone_italian():
    r = classify_fast("Il vostro migliore piatto, subito! Non bado al prezzo")
    assert r is not None
    assert r.archetype == "Astrobarone"


def test_astrobarone_english():
    r = classify_fast("Give me the finest, most exclusive dish. Money is no object")
    assert r is not None
    assert r.archetype == "Astrobarone"


def test_saggi_italian():
    r = classify_fast("Con calma, cercate qualcosa di eccellente e raro")
    assert r is not None
    assert r.archetype == "Saggi del Cosmo"


def test_saggi_english():
    r = classify_fast("Take your time, I seek an extraordinary cosmic experience")
    assert r is not None
    assert r.archetype == "Saggi del Cosmo"


def test_famiglie_italian():
    r = classify_fast("Qualcosa di equilibrato per la famiglia, non troppo caro")
    assert r is not None
    assert r.archetype == "Famiglie Orbitali"


def test_famiglie_english():
    r = classify_fast("Something balanced and affordable for the kids")
    assert r is not None
    assert r.archetype == "Famiglie Orbitali"


def test_ambiguous_returns_none():
    """A truly ambiguous order has no archetype signals -> should return None."""
    r = classify_fast("Vorrei la Nebulosa Stellare")
    assert r is None


def test_empty_returns_none():
    r = classify_fast("")
    assert r is None


def test_classifier_init_no_datapizza():
    """ArchetypeClassifier should init without importing datapizza."""
    c = ArchetypeClassifier()
    assert c.stats["total"] == 0


def test_classify_sync():
    c = ArchetypeClassifier()
    r = c.classify_sync("Datemi qualcosa di veloce, economico")
    assert r.archetype == "Esploratore Galattico"
    assert r.method == "rules"


def test_classify_sync_ambiguous():
    c = ArchetypeClassifier()
    r = c.classify_sync("Vorrei la Nebulosa Stellare")
    assert r.archetype == "unknown"


def test_cache_works():
    c = ArchetypeClassifier()
    r1 = c.classify_sync("Quick and cheap please")
    r2 = c.classify_sync("Quick and cheap please")
    assert r1.archetype == r2.archetype
    assert c.stats["cache_hits"] >= 1


def test_pipeline_imports():
    """Verify pipeline can still be imported with new classifier."""
    from src.serving.pipeline import ServingPipeline, PendingPreparation, ServingMetrics  # noqa: F401
