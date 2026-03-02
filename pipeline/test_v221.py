"""
Quick validation test for ECL v2.2.1 enhancements.
Tests the new functions without full pipeline execution.
"""
import sys
from pathlib import Path

# Add pipeline to path
sys.path.insert(0, str(Path(__file__).parent))

from ecl_formatter import (
    _find_substantive_start,
    _strip_boilerplate_paragraphs,
    _truncate_on_sentence,
    _extract_statute_references,
    _extract_phrases,
    _is_likely_name,
    _score_keyword_candidate,
    extract_keywords,
    extract_retrieval_anchor
)
from config import CONFIG

# Test case: Sample FCA text with boilerplate
TEST_TEXT = """
Date: 20100610

Dockets: A-353-09

Citation: 2010 FCA 150

CORAM: LÉTOURNEAU J.A.
       NADON J.A.
       PELLETIER J.A.

BETWEEN:

RODRIGUE CHARTIER ET AL.

Applicants

and

ATTORNEY GENERAL OF CANADA

Respondent

Heard at Montréal, Quebec, on May 19, 2010.

Judgment delivered at Ottawa, Ontario, on June 10, 2010.

REASONS FOR JUDGMENT

LÉTOURNEAU J.A.

Issues

[1] The three applications for judicial review raise the following three questions:

a) did the Umpire err in concluding that the 36-month limitation period prescribed by section 52 of the Employment Insurance Act, S.C. 1996, c. 23 (Act), does not apply to repayments of overpayments of benefits under section 46 of that Act;

b) did the Umpire err in law in not rescinding the notice issued by the Commission under section 46 of the Act for an allocation of earnings beginning on October 7, 2002, even though he determined that the allocation had to be made beginning the week of December 20, 2004; and

c) did the Umpire err in intervening to restore the Commission's decision that the $1,000 paid for the loss or reduction of benefits constituted earnings within the meaning of subsection 35(2) of the Employment Insurance Regulations, SOR/96-332?

[2] The first two questions are common to all three cases. The third arises only in docket A-354-09. The applicant, Mr. Chartier, is seeking a remedy for himself and a number of his colleagues, all affected by the collapse of their employer, Mine Jeffrey Inc.
"""

def test_substantive_start():
    """Test finding substantive content start."""
    print("\n1. Testing _find_substantive_start()...")
    pos = _find_substantive_start(TEST_TEXT)
    print(f"   Substantive start at position: {pos}")
    print(f"   Text at position: {TEST_TEXT[pos:pos+50]}...")
    assert '[1]' in TEST_TEXT[pos:pos+10], "Should start at [1]"
    print("   ✓ PASS: Correctly identifies paragraph [1]")

def test_boilerplate_stripping():
    """Test boilerplate paragraph removal."""
    print("\n2. Testing _strip_boilerplate_paragraphs()...")
    pos = _find_substantive_start(TEST_TEXT)
    clean = _strip_boilerplate_paragraphs(TEST_TEXT, pos)
    print(f"   Original length: {len(TEST_TEXT)} chars")
    print(f"   Cleaned length: {len(clean)} chars")
    print(f"   Reduction: {len(TEST_TEXT) - len(clean)} chars")
    assert 'CORAM' not in clean[:200], "CORAM should be stripped"
    assert 'Dockets' not in clean[:200], "Dockets should be stripped"
    assert '[1]' in clean[:100] or 'three applications' in clean[:200], "Substantive content should remain"
    print("   ✓ PASS: Boilerplate stripped, substance retained")

def test_retrieval_anchor():
    """Test enhanced RETRIEVAL_ANCHOR extraction."""
    print("\n3. Testing extract_retrieval_anchor()...")
    anchor = extract_retrieval_anchor(TEST_TEXT, max_chars=400)
    print(f"   Anchor length: {len(anchor)} chars")
    print(f"   Anchor starts: {anchor[:100]}...")
    assert len(anchor) <= 400, "Should respect max_chars"
    assert 'Dockets' not in anchor[:100], "Should not start with Dockets"
    assert 'CORAM' not in anchor[:100], "Should not start with CORAM"
    print("   ✓ PASS: Anchor is substance-first")

def test_phrase_extraction():
    """Test multi-word phrase extraction."""
    print("\n4. Testing _extract_phrases()...")
    phrases = CONFIG.get('ei_lexicon_en', {})
    found = _extract_phrases(TEST_TEXT, phrases)
    print(f"   Found phrases: {list(found.keys())}")
    assert 'employment insurance' in found, "Should find 'employment insurance'"
    print("   ✓ PASS: Multi-word phrases extracted")

def test_statute_extraction():
    """Test statute reference extraction."""
    print("\n5. Testing _extract_statute_references()...")
    patterns = CONFIG.get('statute_reference_patterns', [])
    refs = _extract_statute_references(TEST_TEXT, patterns)
    print(f"   Found references: {refs}")
    assert any('section' in r or 's.' in r for r in refs), "Should find section references"
    print("   ✓ PASS: Statute references extracted")

def test_name_filtering():
    """Test judge name filtering."""
    print("\n6. Testing _is_likely_name()...")
    names = ['LÉTOURNEAU', 'NADON', 'Pelletier', 'Chartier']
    patterns = CONFIG.get('name_filter_patterns', [])
    judge_surnames = CONFIG.get('common_judge_surnames', set())
    ei_lexicon = {**CONFIG.get('ei_lexicon_en', {}), **CONFIG.get('ei_lexicon_fr', {})}
    
    for name in names:
        is_name = _is_likely_name(name, patterns, ei_lexicon, judge_surnames)
        print(f"   {name}: {'NAME' if is_name else 'NOT NAME'}")
        assert is_name, f"{name} should be identified as name"
    
    # Test EI term NOT filtered as name
    is_commission_name = _is_likely_name('commission', patterns, ei_lexicon, judge_surnames)
    print(f"   commission: {'NAME' if is_commission_name else 'NOT NAME'}")
    assert not is_commission_name, "EI term 'commission' should not be filtered as name"
    print("   ✓ PASS: Names detected, EI terms preserved")

def test_keyword_extraction():
    """Test EI-aware keyword extraction."""
    print("\n7. Testing extract_keywords()...")
    keywords = extract_keywords(TEST_TEXT, config=CONFIG, max_keywords=7)
    print(f"   Keywords: {keywords}")
    kw_list = [k.strip() for k in keywords.split(',')]
    
    # Should have EI terms
    ei_terms_found = any(
        term in keywords.lower() 
        for term in ['employment', 'insurance', 'benefits', 'commission', 'umpire', 'earnings']
    )
    assert ei_terms_found, "Should extract EI-related terms"
    
    # Should NOT have judge names
    assert 'létourneau' not in keywords.lower(), "Should not include judge surnames"
    assert 'nadon' not in keywords.lower(), "Should not include judge surnames"
    assert 'pelletier' not in keywords.lower(), "Should not include judge surnames"
    
    print("   ✓ PASS: EI terms found, names filtered")

def test_scoring():
    """Test keyword scoring logic."""
    print("\n8. Testing _score_keyword_candidate()...")
    ei_lexicon = {**CONFIG.get('ei_lexicon_en', {}), **CONFIG.get('ei_lexicon_fr', {})}
    statute_refs = ['section 52', 'section 46']
    
    # Test EI term scoring
    score_benefits = _score_keyword_candidate('benefits', 5, TEST_TEXT, ei_lexicon, statute_refs)
    score_generic = _score_keyword_candidate('person', 5, TEST_TEXT, ei_lexicon, statute_refs)
    score_section = _score_keyword_candidate('section', 8, TEST_TEXT, ei_lexicon, statute_refs)
    
    print(f"   'benefits' (EI term): {score_benefits}")
    print(f"   'person' (generic): {score_generic}")
    print(f"   'section' (statute): {score_section}")
    
    assert score_benefits > score_generic, "EI terms should score higher than generic"
    assert score_section > score_generic, "Statute terms should score higher than generic"
    print("   ✓ PASS: Scoring logic working")

if __name__ == '__main__':
    print("="*70)
    print("ECL v2.2.1 VALIDATION TESTS")
    print("="*70)
    
    try:
        test_substantive_start()
        test_boilerplate_stripping()
        test_retrieval_anchor()
        test_phrase_extraction()
        test_statute_extraction()
        test_name_filtering()
        test_keyword_extraction()
        test_scoring()
        
        print("\n" + "="*70)
        print("ALL TESTS PASSED ✓")
        print("="*70)
        print("\nECL v2.2.1 enhancements are working correctly!")
        print("Ready to run full corpus generation.")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
