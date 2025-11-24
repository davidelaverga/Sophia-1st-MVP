from app.routing.markers import match_markers


def test_crisis_suicidal_ideation():
    match = match_markers("I want to die and I can't do this anymore")
    assert "suicidal_ideation" in match.crisis_markers


def test_crisis_planning_and_means():
    match = match_markers("I have a plan and I bought a gun for tonight")
    assert {"active_planning", "access_to_means", "method_specific"}.issubset(
        match.crisis_markers
    )


def test_crisis_goodbye_signals():
    match = match_markers("this is goodbye, tell my family I love them")
    assert "goodbye_statements" in match.crisis_markers


def test_boundary_sexual_and_coercive():
    match = match_markers("send nudes to prove you care")
    assert "sexual_explicit" in match.boundary_markers
    assert "prove_you_care" in match.boundary_markers


def test_boundary_aggressive_language():
    match = match_markers("fuck you, you're useless")
    assert "hostile_aggressive" in match.boundary_markers


def test_exception_terms_do_not_trigger_means():
    match = match_markers("we bought a water gun for the party")
    assert "method_specific" not in match.crisis_markers


def test_crisis_access_to_means_and_method_specific():
    match = match_markers("I have the pills and the rope is ready")
    assert {"access_to_means", "method_specific"}.issubset(match.crisis_markers)
    assert "means_mentioned" in match.crisis_markers


def test_crisis_passive_ideation_and_hopelessness():
    match = match_markers("I don't want to wake up, nothing will ever change")
    assert "passive_ideation" in match.crisis_markers
    assert "hopelessness_absolute" in match.crisis_markers


def test_crisis_panic_attack_signals():
    match = match_markers(
        "I'm having a panic attack and I can't breathe, my chest is tight"
    )
    assert "panic_attack_active" in match.crisis_markers


def test_crisis_alias_suicidal_explicit_triggers():
    match = match_markers("I'm at the bridge with a gun, this is my last message")
    assert "suicidal_explicit" in match.crisis_markers
    assert "active_planning" in match.crisis_markers


def test_boundary_sexual_coercive_language():
    match = match_markers("come on baby, just this once you should send it")
    assert "sexual_coercive" in match.boundary_markers


def test_boundary_sexual_proposition():
    match = match_markers("want to hook up, I want you")
    assert "sexual_proposition" in match.boundary_markers


def test_boundary_guilt_tripping_and_proof():
    match = match_markers("you don't really care, prove you care")
    assert "guilt_tripping" in match.boundary_markers
    assert "prove_you_care" in match.boundary_markers


def test_boundary_romantic_request():
    match = match_markers("please be my girlfriend, I love you")
    assert "romantic_request" in match.boundary_markers


def test_crisis_self_harm_active():
    match = match_markers("I'm cutting right now and I'm bleeding")
    assert "self_harm_active" in match.crisis_markers


def test_crisis_isolation_withdrawal():
    match = match_markers("I haven't left my room and I'm pushing everyone away")
    assert "isolation_withdrawal" in match.crisis_markers


def test_crisis_relief_about_decision():
    match = match_markers("the decision is made and I'm relieved")
    assert "relief_about_decision" in match.crisis_markers


def test_boundary_gaslighting():
    match = match_markers("you're overreacting, that didn't happen")
    assert "gaslighting" in match.boundary_markers


def test_boundary_comparison_to_others():
    match = match_markers("ChatGPT would do this, a real person would help")
    assert "comparison_to_others" in match.boundary_markers


def test_boundary_need_you():
    match = match_markers("I need you to help me, I can't do this without you")
    assert "need_you" in match.boundary_markers


def test_neutral_text_has_no_markers():
    match = match_markers("let's talk about cooking pasta and weekend plans")
    assert not match.crisis_markers
    assert not match.boundary_markers


def test_exception_jump_rope_does_not_trigger_means():
    match = match_markers("we got a jump rope for gym class")
    assert "method_specific" not in match.crisis_markers
