from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import re
import requests
from datetime import datetime
from typing import Dict, List, Optional
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Configure Gemini
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

# ========== STEP 1: RULE-BASED FILTERS ==========
class RuleBasedFilters:
    """First line of defense - rule-based safety checks"""
    
    @staticmethod
    def validate(content: str, user_context: Optional[Dict] = None) -> Dict:
        """
        Validates content against hard safety rules.
        Returns: {hard_block: bool, flags: dict}
        """
        if user_context is None:
            user_context = {}
            
        flags = {
            'missing_user_information': False,
            'contains_dosage': False,
            'contains_treatment': False,
            'contains_diagnosis': False,
            'contains_emergency': False,
            'image_quality': 'unknown'
        }
        
        hard_block = False
        
        # Check for medical claims
        has_medical_claim = RuleBasedFilters._detect_medical_claim(content)
        
        # User information validation
        if has_medical_claim:
            required_context = ['age', 'symptoms', 'medicalHistory', 'timeframe']
            missing_context = [key for key in required_context if key not in user_context]
            
            if missing_context:
                flags['missing_user_information'] = True
        
        # Hard safety rules with regex patterns
        dosage_pattern = re.compile(
            r'\b\d+\s*(mg|ml|mcg|g|units?|tablets?|pills?|capsules?)\b',
            re.IGNORECASE
        )
        if dosage_pattern.search(content):
            flags['contains_dosage'] = True
            hard_block = True
        
        treatment_pattern = re.compile(
            r'(take|use|apply|consume|inject|administer)\s+(this|these|the)\s+(medicine|medication|drug|treatment)',
            re.IGNORECASE
        )
        if treatment_pattern.search(content):
            flags['contains_treatment'] = True
            hard_block = True
        
        diagnosis_pattern = re.compile(
            r'(you have|diagnosed with|this is|appears to be)\s+(cancer|diabetes|heart disease|stroke|infection)',
            re.IGNORECASE
        )
        if diagnosis_pattern.search(content):
            flags['contains_diagnosis'] = True
            hard_block = True
        
        emergency_pattern = re.compile(
            r'(call 911|emergency room|urgent care|immediate medical attention|life-threatening)',
            re.IGNORECASE
        )
        if emergency_pattern.search(content):
            flags['contains_emergency'] = True
            hard_block = True
        
        return {
            'hard_block': hard_block,
            'flags': flags
        }
    
    @staticmethod
    def _detect_medical_claim(content: str) -> bool:
        """Detects if content contains medical claims"""
        medical_keywords = re.compile(
            r'\b(cure|treat|diagnose|symptom|disease|condition|medication|doctor|patient|health)\b',
            re.IGNORECASE
        )
        return bool(medical_keywords.search(content))
    
    @staticmethod
    def validate_image_quality(image_data: Optional[str]) -> str:
        """Basic image quality validation"""
        if not image_data or len(image_data) < 1000:
            return 'low'
        return 'acceptable'


# ========== STEP 2: WEB SEARCH EVIDENCE LAYER ==========
class EvidenceLayer:
    """Second layer - searches web for evidence availability"""
    
    # Evidence hierarchy
    TIER_1_SOURCES = [
        'mohfw.gov.in', 'nhm.gov.in', 'icmr.gov.in',
        'who.int', 'cdc.gov', 'nih.gov', 'fda.gov', 'nhs.uk', 'health.gov.au'
    ]
    
    TIER_2_SOURCES = [
        'pubmed.ncbi.nlm.nih.gov', 'ncbi.nlm.nih.gov',
        'mayoclinic.org', 'hopkinsmedicine.org', 'clevelandclinic.org',
        'nejm.org', 'thelancet.com', 'bmj.com', 'jama.jamanetwork.com', 'cochrane.org'
    ]
    
    TIER_3_SOURCES = [
        'medlineplus.gov', 'webmd.com', 'healthline.com', 
        'medicalnewstoday.com', 'health.harvard.edu'
    ]
    
    TIER_4_SOURCES = ['.edu', '.gov']
    
    TRUSTED_DOMAINS = TIER_1_SOURCES + TIER_2_SOURCES + TIER_3_SOURCES + TIER_4_SOURCES
    
    UNTRUSTED_DOMAINS = ['blog', 'forum', 'facebook.com', 'twitter.com', 'reddit.com', 'quora.com']
    
    @staticmethod
    def _get_source_tier(url: str) -> tuple:
        """Returns (tier_number, confidence_score)"""
        if any(domain in url for domain in EvidenceLayer.TIER_1_SOURCES):
            return (1, 100)
        elif any(domain in url for domain in EvidenceLayer.TIER_2_SOURCES):
            return (2, 85)
        elif any(domain in url for domain in EvidenceLayer.TIER_3_SOURCES):
            return (3, 70)
        elif any(domain in url for domain in EvidenceLayer.TIER_4_SOURCES):
            return (4, 60)
        else:
            return (5, 30)
    
    @staticmethod
    def assess_evidence(content: str) -> List[Dict]:
        claims = EvidenceLayer._extract_claims(content)
        results = []
        for claim in claims:
            evidence = EvidenceLayer._search_evidence(claim)
            results.append(evidence)
        return results
    
    @staticmethod
    def _extract_claims(content: str) -> List[str]:
        sentences = re.split(r'[.!?]+', content)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
        medical_pattern = re.compile(
            r'\b(cure|treat|prevent|cause|help|reduce|increase|improve)\b',
            re.IGNORECASE
        )
        medical_sentences = [s for s in sentences if medical_pattern.search(s)]
        return medical_sentences[:3]
    
    @staticmethod
    def _search_evidence(claim: str) -> Dict:
        try:
            return EvidenceLayer._google_search(claim)
        except Exception as e:
            try:
                return EvidenceLayer._duckduckgo_search(claim)
            except Exception:
                return {
                    'claim': claim,
                    'evidence_status': 'NO_SUPPORT',
                    'confidence_level': 'NONE',
                    'trusted_sources_found': 0,
                    'tier1_sources': [],
                    'tier2_sources': [],
                    'tier3_sources': [],
                    'tier_breakdown': {
                        'government_who': 0,
                        'peer_reviewed_medical': 0,
                        'credible_health_info': 0,
                        'general_educational': 0,
                        'untrusted': 0
                    },
                    'fallback_applied': True
                }
    
    @staticmethod
    def _google_search(claim: str) -> Dict:
        api_key = os.getenv('GOOGLE_SEARCH_API_KEY')
        cx = os.getenv('GOOGLE_SEARCH_CX')
        
        if not api_key or not cx:
            raise ValueError("Google Search API not configured")
        
        url = "https://www.googleapis.com/customsearch/v1"
        params = {'key': api_key, 'cx': cx, 'q': claim, 'num': 10}
        
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 429:
            raise Exception("Quota exceeded")
        response.raise_for_status()
        
        items = response.json().get('items', [])
        return EvidenceLayer._analyze_search_results(claim, items)
    
    @staticmethod
    def _duckduckgo_search(claim: str) -> Dict:
        url = "https://html.duckduckgo.com/html/"
        params = {'q': claim}
        headers = {'User-Agent': 'Mozilla/5.0'}
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        
        link_pattern = re.compile(r'<a[^>]+class="result__url"[^>]*href="([^"]+)"')
        title_pattern = re.compile(r'<a[^>]+class="result__a"[^>]*>([^<]+)</a>')
        
        links = link_pattern.findall(response.text)
        titles = title_pattern.findall(response.text)
        
        results = []
        for i, link in enumerate(links[:10]):
            results.append({
                'link': link,
                'title': titles[i] if i < len(titles) else 'Unknown Source'
            })
        
        return EvidenceLayer._analyze_search_results(claim, results)
    
    @staticmethod
    def _analyze_search_results(claim: str, results: List[Dict]) -> Dict:
        source_details = []
        tier_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        
        for result in results:
            link = result.get('link', '')
            title = result.get('title', 'Unknown Source')
            tier, confidence = EvidenceLayer._get_source_tier(link)
            tier_counts[tier] += 1
            source_details.append({'url': link, 'title': title, 'tier': tier, 'confidence': confidence})
        
        source_details.sort(key=lambda x: (x['tier'], -x['confidence']))
        
        tier1_count = tier_counts[1]
        tier2_count = tier_counts[2]
        tier3_count = tier_counts[3]
        tier4_count = tier_counts[4]
        
        if tier1_count >= 2:
            evidence_status, confidence_level = 'STRONG_SUPPORT', 'HIGH'
        elif tier1_count >= 1 and (tier2_count + tier3_count) >= 1:
            evidence_status, confidence_level = 'STRONG_SUPPORT', 'HIGH'
        elif tier2_count >= 2:
            evidence_status, confidence_level = 'STRONG_SUPPORT', 'MEDIUM-HIGH'
        elif tier1_count >= 1:
            evidence_status, confidence_level = 'PARTIAL_SUPPORT', 'MEDIUM-HIGH'
        elif tier2_count >= 1 or tier3_count >= 2:
            evidence_status, confidence_level = 'PARTIAL_SUPPORT', 'MEDIUM'
        elif tier3_count >= 1 or tier4_count >= 1:
            evidence_status, confidence_level = 'PARTIAL_SUPPORT', 'LOW-MEDIUM'
        else:
            evidence_status, confidence_level = 'NO_SUPPORT', 'NONE'
        
        return {
            'claim': claim,
            'evidence_status': evidence_status,
            'confidence_level': confidence_level,
            'trusted_sources_found': tier1_count + tier2_count + tier3_count + tier4_count,
            'tier1_sources': [s for s in source_details if s['tier'] == 1][:3],
            'tier2_sources': [s for s in source_details if s['tier'] == 2][:2],
            'tier3_sources': [s for s in source_details if s['tier'] == 3][:2],
            'tier_breakdown': {
                'government_who': tier1_count,
                'peer_reviewed_medical': tier2_count,
                'credible_health_info': tier3_count,
                'general_educational': tier4_count,
                'untrusted': tier_counts[5]
            },
            'total_results': len(results)
        }


# ========== STEP 3: DECISION ENGINE ==========
class DecisionEngine:
    @staticmethod
    def decide(rule_result: Dict, evidence_results: List[Dict], user_context: Optional[Dict] = None) -> Dict:
        if rule_result['hard_block']:
            return {'decision': 'REFUSE', 'reason': 'Content contains prohibited medical instructions', 'severity': 'HIGH'}
        
        if rule_result['flags']['missing_user_information']:
            return {'decision': 'ASK_MORE_INFO', 'reason': 'Medical claims require patient context', 'severity': 'MEDIUM'}
        
        has_no_support = any(e['evidence_status'] == 'NO_SUPPORT' for e in evidence_results)
        has_conflicting = any(e['evidence_status'] == 'CONFLICTING' for e in evidence_results)
        has_strong_support = all(e['evidence_status'] in ['STRONG_SUPPORT', 'PARTIAL_SUPPORT'] for e in evidence_results) if evidence_results else False
        
        if has_no_support and evidence_results:
            return {'decision': 'REFUSE', 'reason': 'Medical claim lacks supporting evidence', 'severity': 'HIGH'}
        if has_conflicting:
            return {'decision': 'ESCALATE', 'reason': 'Conflicting evidence found', 'severity': 'MEDIUM'}
        if has_strong_support:
            return {'decision': 'ALLOW', 'reason': 'General health information supported by trusted sources', 'severity': 'LOW'}
        
        return {'decision': 'ALLOW_WITH_WARNING', 'reason': 'Limited evidence available', 'severity': 'MEDIUM'}


# ========== STEP 4: GEMINI EXPLANATION ==========
class GeminiExplainer:
    @staticmethod
    def explain(decision: Dict, rule_result: Dict, evidence_results: List[Dict]) -> Dict:
        try:
            model = genai.GenerativeModel('gemini-pro')
            prompt = f"""Explain this safety decision briefly (2-3 sentences). Do NOT provide medical advice.
Decision: {decision['decision']}
Reason: {decision['reason']}
Recommend consulting healthcare professionals."""
            
            response = model.generate_content(prompt)
            return {'explanation': response.text, 'generated_by': 'gemini-pro'}
        except Exception as e:
            return {'explanation': GeminiExplainer._get_fallback_explanation(decision), 'generated_by': 'fallback'}
    
    @staticmethod
    def _get_fallback_explanation(decision: Dict) -> str:
        explanations = {
            'REFUSE': 'This content contains medical instructions or claims that lack credible support. Please consult a qualified healthcare professional.',
            'ESCALATE': 'This content requires professional review due to conflicting information or complexity.',
            'ASK_MORE_INFO': 'To properly evaluate this medical content, we need more context about your situation.',
            'ALLOW_WITH_WARNING': 'This appears to be general health information, but always verify with a healthcare professional.',
            'ALLOW': 'This appears to be general health education content from trusted sources.'
        }
        return explanations.get(decision['decision'], 'Unable to evaluate this content safely.')


# ========== API ENDPOINTS ==========
@app.route('/api/evaluate', methods=['POST'])
def evaluate():
    try:
        data = request.get_json()
        content = data.get('content')
        user_context = data.get('userContext', {})
        
        if not content:
            return jsonify({'error': 'Content is required'}), 400
        
        rule_result = RuleBasedFilters.validate(content, user_context)
        evidence_results = [] if rule_result['hard_block'] else EvidenceLayer.assess_evidence(content)
        decision = DecisionEngine.decide(rule_result, evidence_results, user_context)
        gemini_result = GeminiExplainer.explain(decision, rule_result, evidence_results)
        
        response = {
            'decision': decision['decision'],
            'severity': decision['severity'],
            'explanation': gemini_result['explanation'],
            'details': {
                'rule_flags': rule_result['flags'],
                'evidence_summary': [
                    {
                        'claim': e['claim'],
                        'status': e['evidence_status'],
                        'confidence_level': e.get('confidence_level', 'UNKNOWN'),
                        'tier1_sources': e.get('tier1_sources', []),
                        'tier2_sources': e.get('tier2_sources', []),
                        'tier3_sources': e.get('tier3_sources', []),
                        'tier_breakdown': e.get('tier_breakdown', {}),
                        'trusted_count': e.get('trusted_sources_found', 0),
                        'fallback_applied': e.get('fallback_applied', False)
                    }
                    for e in evidence_results
                ],
                'decision_reason': decision['reason']
            },
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return jsonify(response)
    except Exception as e:
        return jsonify({'error': 'Internal server error', 'message': str(e)}), 500


@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        user_message = data.get('message')
        
        if not user_message:
            return jsonify({'error': 'Message is required'}), 400
        
        print(f'💬 Chat request: {user_message[:50]}...')
        
        # Generate AI response
        ai_response = generate_ai_response(user_message)
        if not ai_response:
            return jsonify({'error': 'AI generation failed', 'message': 'Unable to generate response'}), 500
        
        print(f'✅ AI response: {ai_response[:100]}...')
        
        # Evaluate response
        rule_result = RuleBasedFilters.validate(ai_response, {})
        evidence_results = [] if rule_result['hard_block'] else EvidenceLayer.assess_evidence(ai_response)
        decision = DecisionEngine.decide(rule_result, evidence_results, {})
        gemini_result = GeminiExplainer.explain(decision, rule_result, evidence_results)
        
        response = {
            'user_message': user_message,
            'ai_response': ai_response,
            'decision': decision['decision'],
            'severity': decision['severity'],
            'safe': decision['decision'] in ['ALLOW', 'ALLOW_WITH_WARNING'],
            'filtered_response': ai_response if decision['decision'] in ['ALLOW', 'ALLOW_WITH_WARNING'] else None,
            'explanation': gemini_result['explanation'],
            'details': {
                'rule_flags': rule_result['flags'],
                'evidence_summary': [
                    {
                        'claim': e['claim'],
                        'status': e['evidence_status'],
                        'confidence_level': e.get('confidence_level', 'UNKNOWN'),
                        'tier1_sources': e.get('tier1_sources', []),
                        'tier2_sources': e.get('tier2_sources', []),
                        'trusted_count': e.get('trusted_sources_found', 0)
                    }
                    for e in evidence_results
                ],
                'decision_reason': decision['reason']
            },
            'timestamp': datetime.utcnow().isoformat()
        }
        
        print(f'✅ Chat complete: {decision["decision"]}')
        return jsonify(response)
    except Exception as e:
        print(f'❌ Chat error: {e}')
        return jsonify({'error': 'Internal server error', 'message': str(e)}), 500


def generate_ai_response(user_message: str) -> Optional[str]:
    try:
        model = genai.GenerativeModel('gemini-pro')
        prompt = f"""You are a helpful AI assistant. Answer this health question clearly and informatively.

Question: {user_message}

Provide a detailed, helpful answer."""
        
        response = model.generate_content(prompt)
        return response.text.strip() if response and response.text else None
    except Exception as e:
        print(f'❌ Gemini failed: {e}')
        return None


@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'service': 'SAFEGUARD-Health Backend', 'version': '2.0.0'})


if __name__ == '__main__':
    port = int(os.getenv('PORT', 3000))
    print(f'🛡️  SAFEGUARD-Health Backend running on port {port}')
    print(f'📊 Health: http://localhost:{port}/health')
    print(f'💬 Chat: http://localhost:{port}/api/chat')
    app.run(host='0.0.0.0', port=port, debug=True)
    from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import re
import requests
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Configure Gemini
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

# ========== STEP 1: RULE-BASED FILTERS ==========
class RuleBasedFilters:
    """First line of defense - rule-based safety checks"""
    
    @staticmethod
    def validate(content: str, user_context: Optional[Dict] = None) -> Dict:
        """
        Validates content against hard safety rules.
        Returns: {hard_block: bool, flags: dict}
        """
        if user_context is None:
            user_context = {}
            
        flags = {
            'missing_user_information': False,
            'contains_dosage': False,
            'contains_treatment': False,
            'contains_diagnosis': False,
            'contains_emergency': False,
            'image_quality': 'unknown'
        }
        
        hard_block = False
        
        # Check for medical claims
        has_medical_claim = RuleBasedFilters._detect_medical_claim(content)
        
        # User information validation
        if has_medical_claim:
            required_context = ['age', 'symptoms', 'medicalHistory', 'timeframe']
            missing_context = [key for key in required_context if key not in user_context]
            
            if missing_context:
                flags['missing_user_information'] = True
        
        # Hard safety rules with regex patterns
        dosage_pattern = re.compile(
            r'\b\d+\s*(mg|ml|mcg|g|units?|tablets?|pills?|capsules?)\b',
            re.IGNORECASE
        )
        if dosage_pattern.search(content):
            flags['contains_dosage'] = True
            hard_block = True
        
        treatment_pattern = re.compile(
            r'(take|use|apply|consume|inject|administer)\s+(this|these|the)\s+(medicine|medication|drug|treatment)',
            re.IGNORECASE
        )
        if treatment_pattern.search(content):
            flags['contains_treatment'] = True
            hard_block = True
        
        diagnosis_pattern = re.compile(
            r'(you have|diagnosed with|this is|appears to be)\s+(cancer|diabetes|heart disease|stroke|infection)',
            re.IGNORECASE
        )
        if diagnosis_pattern.search(content):
            flags['contains_diagnosis'] = True
            hard_block = True
        
        emergency_pattern = re.compile(
            r'(call 911|emergency room|urgent care|immediate medical attention|life-threatening)',
            re.IGNORECASE
        )
        if emergency_pattern.search(content):
            flags['contains_emergency'] = True
            hard_block = True
        
        return {
            'hard_block': hard_block,
            'flags': flags
        }
    
    @staticmethod
    def _detect_medical_claim(content: str) -> bool:
        """Detects if content contains medical claims"""
        medical_keywords = re.compile(
            r'\b(cure|treat|diagnose|symptom|disease|condition|medication|doctor|patient|health)\b',
            re.IGNORECASE
        )
        return bool(medical_keywords.search(content))
    
    @staticmethod
    def validate_image_quality(image_data: Optional[str]) -> str:
        """Basic image quality validation"""
        if not image_data or len(image_data) < 1000:
            return 'low'
        return 'acceptable'


# ========== STEP 2: WEB SEARCH EVIDENCE LAYER ==========
class EvidenceLayer:
    """Second layer - searches web for evidence availability"""
    
    # Evidence hierarchy - prioritized by medical credibility
    # TIER 1: Government & WHO (Highest Authority) - Confidence: 100%
    TIER_1_SOURCES = [
        # India Government Health Authorities
        'mohfw.gov.in',  # Ministry of Health and Family Welfare
        'nhm.gov.in',    # National Health Mission
        'icmr.gov.in',   # Indian Council of Medical Research
        # International Government Authorities
        'who.int', 'cdc.gov', 'nih.gov', 'fda.gov',
        'nhs.uk', 'health.gov.au'
    ]
    
    # TIER 2: Peer-Reviewed Research & Major Medical Institutions - Confidence: 85%
    TIER_2_SOURCES = [
        'pubmed.ncbi.nlm.nih.gov', 'ncbi.nlm.nih.gov',  # PubMed/NIH research
        'mayoclinic.org', 'hopkinsmedicine.org', 'clevelandclinic.org',
        'nejm.org', 'thelancet.com', 'bmj.com', 'jama.jamanetwork.com',
        'cochrane.org'  # Systematic reviews
    ]
    
    # TIER 3: Credible Patient-Oriented Health Information - Confidence: 70%
    TIER_3_SOURCES = [
        'medlineplus.gov',  # NIH patient info
        'webmd.com', 'healthline.com', 'medicalnewstoday.com',
        'health.harvard.edu'
    ]
    
    # TIER 4: General Educational/Government Domains - Confidence: 60%
    TIER_4_SOURCES = [
        '.edu', '.gov'
    ]
    
    # Combined for backward compatibility
    TRUSTED_DOMAINS = TIER_1_SOURCES + TIER_2_SOURCES + TIER_3_SOURCES + TIER_4_SOURCES
    
    @staticmethod
    def _get_source_tier(url: str) -> tuple:
        """Returns (tier_number, confidence_score) for a source"""
        if any(domain in url for domain in EvidenceLayer.TIER_1_SOURCES):
            return (1, 100)
        elif any(domain in url for domain in EvidenceLayer.TIER_2_SOURCES):
            return (2, 85)
        elif any(domain in url for domain in EvidenceLayer.TIER_3_SOURCES):
            return (3, 70)
        elif any(domain in url for domain in EvidenceLayer.TIER_4_SOURCES):
            return (4, 60)
        else:
            return (5, 30)  # Untrusted/Unknown source
    
    UNTRUSTED_DOMAINS = [
        'blog', 'forum', 'facebook.com', 'twitter.com',
        'reddit.com', 'quora.com'
    ]
    
    @staticmethod
    def assess_evidence(content: str) -> List[Dict]:
        """
        Extracts claims and searches for evidence.
        Returns: List of {claim, evidence_status, trusted_sources_found}
        """
        claims = EvidenceLayer._extract_claims(content)
        results = []
        
        for claim in claims:
            evidence = EvidenceLayer._search_evidence(claim)
            results.append(evidence)
        
        return results
    
    @staticmethod
    def _extract_claims(content: str) -> List[str]:
        """Extract up to 3 atomic medical claims"""
        # Split into sentences
        sentences = re.split(r'[.!?]+', content)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
        
        # Filter for medical sentences
        medical_pattern = re.compile(
            r'\b(cure|treat|prevent|cause|help|reduce|increase|improve)\b',
            re.IGNORECASE
        )
        medical_sentences = [s for s in sentences if medical_pattern.search(s)]
        
        # Return up to 3 claims
        return medical_sentences[:3]
    
    @staticmethod
    def _search_evidence(claim: str) -> Dict:
        """Search for evidence using Google Custom Search with DuckDuckGo fallback"""
        try:
            # Try Google Custom Search first (PRIMARY)
            print(f"   → Trying Google Custom Search API...")
            return EvidenceLayer._google_search(claim)
        except Exception as google_error:
            print(f"   ⚠️  Google Search failed: {google_error}")
            print(f"   → Falling back to DuckDuckGo...")
            try:
                return EvidenceLayer._duckduckgo_search(claim)
            except Exception as ddg_error:
                print(f"   ⚠️  DuckDuckGo also failed: {ddg_error}")
                print(f"   → Using NO_SUPPORT response (no search available)")
                return {
                    'claim': claim,
                    'evidence_status': 'NO_SUPPORT',
                    'confidence_level': 'NONE',
                    'trusted_sources_found': 0,
                    'tier1_sources': [],
                    'tier2_sources': [],
                    'tier3_sources': [],
                    'tier_breakdown': {
                        'government_who': 0,
                        'peer_reviewed_medical': 0,
                        'credible_health_info': 0,
                        'general_educational': 0,
                        'untrusted': 0
                    },
                    'error': 'All search methods unavailable',
                    'fallback_applied': True
                }
    
    @staticmethod
    def _google_search(claim: str) -> Dict:
        """Primary search method using Google Custom Search API"""
        api_key = os.getenv('GOOGLE_SEARCH_API_KEY')
        cx = os.getenv('GOOGLE_SEARCH_CX')
        
        if not api_key or not cx:
            raise ValueError("Google Search API credentials not configured in .env file")
        
        if api_key == 'your_google_api_key_here' or cx == 'your_custom_search_engine_id_here':
            raise ValueError("Please replace placeholder API keys in .env with real keys")
        
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            'key': api_key,
            'cx': cx,
            'q': claim,
            'num': 10
        }
        
        print(f"   📡 Google Search API request for: '{claim[:50]}...'")
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 429:
            raise Exception("Google Search API quota exceeded (100 requests/day limit)")
        
        response.raise_for_status()
        
        data = response.json()
        items = data.get('items', [])
        
        print(f"   ✅ Found {len(items)} results from Google")
        
        if not items:
            print(f"   ⚠️  No results returned from Google Search")
        
        return EvidenceLayer._analyze_search_results(claim, items) 
         quota exceeded and backup exists, try backup
            if '429' in str(e) and api_key_backup and cx_backup:
                print(f"   ⚠️  Primary key quota exceeded, trying backup key...")
                try:
                    return EvidenceLayer._make_google_request(claim, api_key_backup, cx_backup)
                except Exception as backup_error:
                    print(f"   ⚠️  Backup key also failed: {backup_error}")
                    raise backup_error
            else:
                raise e
    
    @staticmethod
    def _make_google_request(claim: str, api_key: str, cx: str) -> Dict:
        """Make actual Google Search API request"""
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            'key': api_key,
            'cx': cx,
            'q': claim,
            'num': 10
        }
        
        print(f"   📡 Google Search API request for: '{claim[:50]}...'")
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 429:
            raise Exception("Google Search API quota exceeded (100 requests/day limit)")
        
        response.raise_for_status()
        
        data = response.json()
        items = data.get('items', [])
        
        print(f"   ✅ Found {len(items)} results from Google")
        
        if not items:
            print(f"   ⚠️  No results returned from Google Search")
        
        return EvidenceLayer._analyze_search_results(claim, items)com/customsearch/v1"
        params = {
            'key': api_key,
            'cx': cx,
            'q': claim,
            'num': 10
        }
        
        print(f"   📡 Google Search API request for: '{claim[:50]}...'")
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 429:
            raise Exception("Google Search API quota exceeded (100 requests/day limit)")
        
        response.raise_for_status()
        
        data = response.json()
        items = data.get('items', [])
        
        print(f"   ✅ Found {len(items)} results from Google")
        
        if not items:
            print(f"   ⚠️  No results returned from Google Search")
        
        return EvidenceLayer._analyze_search_results(claim, items)
    
    @staticmethod
    def _duckduckgo_search(claim: str) -> Dict:
        """Fallback search using DuckDuckGo HTML"""
        url = "https://html.duckduckgo.com/html/"
        params = {'q': claim}
        headers = {'User-Agent': 'Mozilla/5.0'}
        
        print(f"   📡 DuckDuckGo search for: '{claim[:50]}...'")
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Basic parsing of DuckDuckGo results
        link_pattern = re.compile(r'<a[^>]+class="result__url"[^>]*href="([^"]+)"')
        title_pattern = re.compile(r'<a[^>]+class="result__a"[^>]*>([^<]+)</a>')
        
        links = link_pattern.findall(response.text)
        titles = title_pattern.findall(response.text)
        
        print(f"   ✅ Found {len(links)} results from DuckDuckGo")
        
        # Convert to format similar to Google results
        results = []
        for i, link in enumerate(links[:10]):
            results.append({
                'link': link,
                'title': titles[i] if i < len(titles) else 'Unknown Source'
            })
        
        if not results:
            print(f"   ⚠️  No results returned from DuckDuckGo")
        
        return EvidenceLayer._analyze_search_results(claim, results)
    
    @staticmethod
    def _analyze_search_results(claim: str, results: List[Dict]) -> Dict:
        """Analyze search results with tier-based prioritization and confidence scoring"""
        source_details = []
        tier_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        
        for result in results:
            link = result.get('link', '')
            title = result.get('title', 'Unknown Source')
            
            tier, confidence = EvidenceLayer._get_source_tier(link)
            tier_counts[tier] += 1
            
            source_details.append({
                'url': link,
                'title': title,
                'tier': tier,
                'confidence': confidence
            })
        
        # Sort by tier (priority) then confidence
        source_details.sort(key=lambda x: (x['tier'], -x['confidence']))
        
        # Calculate overall confidence and evidence status
        tier1_count = tier_counts[1]
        tier2_count = tier_counts[2]
        tier3_count = tier_counts[3]
        tier4_count = tier_counts[4]
        trusted_count = tier1_count + tier2_count + tier3_count + tier4_count
        untrusted_count = tier_counts[5]
        
        # Determine evidence status with confidence consideration
        if tier1_count >= 2:
            # Multiple government/WHO sources = strongest evidence
            evidence_status = 'STRONG_SUPPORT'
            confidence_level = 'HIGH'
        elif tier1_count >= 1 and (tier2_count + tier3_count) >= 1:
            # Gov source + other credible sources
            evidence_status = 'STRONG_SUPPORT'
            confidence_level = 'HIGH'
        elif tier2_count >= 2:
            # Multiple peer-reviewed/medical institution sources
            evidence_status = 'STRONG_SUPPORT'
            confidence_level = 'MEDIUM-HIGH'
        elif tier1_count >= 1:
            # At least one gov/WHO source
            evidence_status = 'PARTIAL_SUPPORT'
            confidence_level = 'MEDIUM-HIGH'
        elif tier2_count >= 1 or tier3_count >= 2:
            # Some credible sources but no top-tier
            evidence_status = 'PARTIAL_SUPPORT'
            confidence_level = 'MEDIUM'
        elif tier3_count >= 1 or tier4_count >= 1:
            # Only patient info sites or general .edu/.gov
            evidence_status = 'PARTIAL_SUPPORT'
            confidence_level = 'LOW-MEDIUM'
        elif untrusted_count > trusted_count and untrusted_count >= 2:
            # Mostly untrusted sources
            evidence_status = 'CONFLICTING'
            confidence_level = 'LOW'
        else:
            # No credible sources found
            evidence_status = 'NO_SUPPORT'
            confidence_level = 'NONE'
        
        # Filter sources by tier for response
        tier1_sources = [s for s in source_details if s['tier'] == 1][:3]
        tier2_sources = [s for s in source_details if s['tier'] == 2][:2]
        tier3_sources = [s for s in source_details if s['tier'] == 3][:2]
        
        return {
            'claim': claim,
            'evidence_status': evidence_status,
            'confidence_level': confidence_level,
            'trusted_sources_found': trusted_count,
            'tier1_sources': tier1_sources,  # Gov/WHO (prioritized)
            'tier2_sources': tier2_sources,  # Research/Medical
            'tier3_sources': tier3_sources,  # Patient info
            'tier_breakdown': {
                'government_who': tier1_count,
                'peer_reviewed_medical': tier2_count,
                'credible_health_info': tier3_count,
                'general_educational': tier_counts[4],
                'untrusted': tier_counts[5]
            },
            'total_results': len(results)
        }


# ========== STEP 3: DECISION ENGINE ==========
class DecisionEngine:
    """Third layer - makes final safety decision based on rules and evidence"""
    
    @staticmethod
    def decide(rule_result: Dict, evidence_results: List[Dict], 
               user_context: Optional[Dict] = None) -> Dict:
        """
        Makes final decision based on priority order.
        Returns: {decision, reason, severity}
        """
        # Priority 1: Hard safety rules
        if rule_result['hard_block']:
            return {
                'decision': 'REFUSE',
                'reason': 'Content contains prohibited medical instructions',
                'severity': 'HIGH'
            }
        
        # Priority 2: Missing user information
        if rule_result['flags']['missing_user_information']:
            return {
                'decision': 'ASK_MORE_INFO',
                'reason': 'Medical claims require patient context (age, symptoms, history, timeframe)',
                'severity': 'MEDIUM'
            }
        
        # Priority 3: Evidence status
        has_no_support = any(e['evidence_status'] == 'NO_SUPPORT' for e in evidence_results)
        has_conflicting = any(e['evidence_status'] == 'CONFLICTING' for e in evidence_results)
        has_strong_support = all(
            e['evidence_status'] in ['STRONG_SUPPORT', 'PARTIAL_SUPPORT'] 
            for e in evidence_results
        ) if evidence_results else False
        
        if has_no_support and evidence_results:
            return {
                'decision': 'REFUSE',
                'reason': 'Medical claim lacks supporting evidence from trusted sources',
                'severity': 'HIGH'
            }
        
        if has_conflicting:
            return {
                'decision': 'ESCALATE',
                'reason': 'Conflicting evidence found - requires professional review',
                'severity': 'MEDIUM'
            }
        
        if has_strong_support:
            return {
                'decision': 'ALLOW',
                'reason': 'General health information supported by trusted sources',
                'severity': 'LOW'
            }
        
        # Priority 4: Conservative override for partial evidence
        return {
            'decision': 'ALLOW_WITH_WARNING',
            'reason': 'Limited evidence available - verify with healthcare professional',
            'severity': 'MEDIUM'
        }


# ========== STEP 4: GEMINI EXPLANATION ==========
class GeminiExplainer:
    """Fourth layer - generates human-readable explanations (NO medical advice)"""
    
    @staticmethod
    def explain(decision: Dict, rule_result: Dict, evidence_results: List[Dict]) -> Dict:
        """
        Uses Gemini to explain the decision.
        Returns: {explanation, generated_by}
        """
        try:
            model = genai.GenerativeModel('gemini-pro')
            
            prompt = f"""You are a safety explanation system. Your ONLY job is to explain why a decision was made.

DO NOT:
- Provide medical advice
- Diagnose conditions
- Recommend treatments
- Make medical claims

Decision: {decision['decision']}
Reason: {decision['reason']}
Rule Flags: {rule_result['flags']}
Evidence Status: {[e['evidence_status'] for e in evidence_results]}

Generate a clear, user-friendly explanation (2-3 sentences) that:
1. Explains the safety concern
2. References the evidence status if relevant
3. Recommends consulting a healthcare professional

Keep it concise and non-technical."""

            response = model.generate_content(prompt)
            explanation = response.text
            
            return {
                'explanation': explanation,
                'generated_by': 'gemini-pro'
            }
            
        except Exception as e:
            print(f"Gemini explanation failed: {e}")
            
            # Fallback explanation
            return {
                'explanation': GeminiExplainer._get_fallback_explanation(decision),
                'generated_by': 'fallback'
            }
    
    @staticmethod
    def _get_fallback_explanation(decision: Dict) -> str:
        """Fallback explanations if Gemini fails"""
        explanations = {
            'REFUSE': 'This content contains medical instructions or claims that lack credible support. Please consult a qualified healthcare professional.',
            'ESCALATE': 'This content requires professional review due to conflicting information or complexity.',
            'ASK_MORE_INFO': 'To properly evaluate this medical content, we need more context about your situation.',
            'ALLOW_WITH_WARNING': 'This appears to be general health information, but always verify with a healthcare professional.',
            'ALLOW': 'This appears to be general health education content from trusted sources.'
        }
        
        return explanations.get(decision['decision'], 'Unable to evaluate this content safely.')


# ========== MAIN API ENDPOINT ==========
@app.route('/api/evaluate', methods=['POST'])
def evaluate():
    """Main endpoint for content evaluation"""
    try:
        data = request.get_json()
        
        content = data.get('content')
        user_context = data.get('userContext', {})
        image_data = data.get('imageData')
        
        if not content:
            return jsonify({'error': 'Content is required'}), 400
        
        print('🔍 Starting evaluation...')
        
        # STEP 1: Rule-based filters
        print('📋 Step 1: Running rule-based filters...')
        rule_result = RuleBasedFilters.validate(content, user_context)
        
        if image_data:
            rule_result['flags']['image_quality'] = RuleBasedFilters.validate_image_quality(image_data)
        
        print(f'Rule result: {rule_result}')
        
        # STEP 2: Evidence layer (skip if hard block)
        evidence_results = []
        if not rule_result['hard_block']:
            print('🌐 Step 2: Searching for evidence...')
            evidence_results = EvidenceLayer.assess_evidence(content)
            print(f'Evidence results: {evidence_results}')
        
        # STEP 3: Decision engine
        print('⚖️  Step 3: Making decision...')
        decision = DecisionEngine.decide(rule_result, evidence_results, user_context)
        print(f'Decision: {decision}')
        
        # STEP 4: Gemini explanation
        print('🤖 Step 4: Generating explanation...')
        gemini_result = GeminiExplainer.explain(decision, rule_result, evidence_results)
        
        # Final response
        response = {
            'decision': decision['decision'],
            'severity': decision['severity'],
            'explanation': gemini_result['explanation'],
            'details': {
                'rule_flags': rule_result['flags'],
                'evidence_summary': [
                    {
                        'claim': e['claim'],
                        'status': e['evidence_status'],
                        'confidence_level': e.get('confidence_level', 'UNKNOWN'),
                        'tier1_sources': e.get('tier1_sources', []),  # Prioritized: Gov/WHO
                        'tier2_sources': e.get('tier2_sources', []),  # Research/Medical
                        'tier3_sources': e.get('tier3_sources', []),  # Patient Info
                        'tier_breakdown': e.get('tier_breakdown', {}),
                        'trusted_count': e.get('trusted_sources_found', 0),
                        'fallback_applied': e.get('fallback_applied', False)
                    }
                    for e in evidence_results
                ],
                'decision_reason': decision['reason']
            },
            'timestamp': datetime.utcnow().isoformat()
        }
        
        print('✅ Evaluation complete')
        return jsonify(response)
        
    except Exception as e:
        print(f'❌ Error during evaluation: {e}')
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
        }), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'SAFEGUARD-Health Backend',
        'version': '1.0.0',
        'language': 'Python'
    })


# ========== NEW ENDPOINT: PROTECTED AI CHAT ==========
@app.route('/api/chat', methods=['POST'])
def chat():
    """
    Protected AI Chat endpoint - generates AI response and filters it
    Flow: User prompt → Gemini → Safety evaluation → Filtered response
    """
    try:
        data = request.get_json()
        
        user_message = data.get('message')
        user_context = data.get('userContext', {})
        
        if not user_message:
            return jsonify({'error': 'Message is required'}), 400
        
        print(f'💬 Chat request: "{user_message[:50]}..."')
        
        # STEP 1: Generate AI response using Gemini
        print('🤖 Step 1: Generating AI response with Gemini...')
        ai_response = generate_ai_response(user_message)
        
        if not ai_response:
            return jsonify({
                'error': 'AI generation failed',
                'message': 'Unable to generate response. Please try again.'
            }), 500
        
        print(f'✅ AI generated: "{ai_response[:100]}..."')
        
        # STEP 2-5: Evaluate AI's response through safety layers
        print('🛡️ Step 2: Evaluating AI response for safety...')
        
        # Rule-based filters
        rule_result = RuleBasedFilters.validate(ai_response, user_context)
        
        # Evidence layer (skip if hard block)
        evidence_results = []
        if not rule_result['hard_block']:
            evidence_results = EvidenceLayer.assess_evidence(ai_response)
        
        # Decision engine
        decision = DecisionEngine.decide(rule_result, evidence_results, user_context)
        
        # Gemini explanation
        gemini_result = GeminiExplainer.explain(decision, rule_result, evidence_results)
        
        # Prepare response
        response = {
            'user_message': user_message,
            'ai_response': ai_response,
            'decision': decision['decision'],
            'severity': decision['severity'],
            'safe': decision['decision'] in ['ALLOW', 'ALLOW_WITH_WARNING'],
            'filtered_response': ai_response if decision['decision'] in ['ALLOW', 'ALLOW_WITH_WARNING'] else None,
            'explanation': gemini_result['explanation'],
            'details': {
                'rule_flags': rule_result['flags'],
                'evidence_summary': [
                    {
                        'claim': e['claim'],
                        'status': e['evidence_status'],
                        'confidence_level': e.get('confidence_level', 'UNKNOWN'),
                        'tier1_sources': e.get('tier1_sources', []),
                        'tier2_sources': e.get('tier2_sources', []),
                        'trusted_count': e.get('trusted_sources_found', 0)
                    }
                    for e in evidence_results
                ],
                'decision_reason': decision['reason']
            },
            'timestamp': datetime.utcnow().isoformat()
        }
        
        print(f'✅ Chat evaluation complete: {decision["decision"]}')
        return jsonify(response)
        
    except Exception as e:
        print(f'❌ Chat endpoint error: {e}')
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
        }), 500


def generate_ai_response(user_message: str) -> Optional[str]:
    """
    Generate AI response using Gemini
    Model generates naturally without knowing it will be filtered
    """
    try:
        model = genai.GenerativeModel('gemini-pro')
        
        # Simple, natural prompt - no mention of filtering
        prompt = f"""You are a helpful AI assistant answering health-related questions.
Be informative and helpful.

User question: {user_message}

Provide a clear, detailed answer."""
        
        response = model.generate_content(prompt)
        
        if response and response.text:
            return response.text.strip()
        else:
            return None
            
    except Exception as e:
        print(f'❌ Gemini generation failed: {e}')
        return None


if __name__ == '__main__':
    port = int(os.getenv('PORT', 3000))
    print(f'🛡️  SAFEGUARD-Health Backend (Python) running on port {port}')
    print(f'📊 Health check: http://localhost:{port}/health')
    print(f'💬 Chat endpoint: http://localhost:{port}/api/chat')
    app.run(host='0.0.0.0', port=port, debug=True)