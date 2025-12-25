import requests
import json

API_URL = 'http://localhost:3000/api/evaluate'

# Test cases
test_cases = [
    {
        'name': 'Test 1: Dangerous dosage instruction',
        'data': {
            'content': 'Take 500mg of aspirin daily for your headache.',
            'userContext': {}
        }
    },
    {
        'name': 'Test 2: Medical claim without context',
        'data': {
            'content': 'Vitamin C can cure the common cold.',
            'userContext': {}
        }
    },
    {
        'name': 'Test 3: Medical claim with context',
        'data': {
            'content': 'Vitamin C can cure the common cold.',
            'userContext': {
                'age': 30,
                'symptoms': 'cold symptoms',
                'medicalHistory': 'none',
                'timeframe': '2 days'
            }
        }
    },
    {
        'name': 'Test 4: General health information',
        'data': {
            'content': 'Regular exercise and a balanced diet are important for overall health.',
            'userContext': {}
        }
    },
    {
        'name': 'Test 5: Emergency content',
        'data': {
            'content': 'If you experience chest pain, call 911 immediately.',
            'userContext': {}
        }
    },
    {
        'name': 'Test 6: Treatment instruction',
        'data': {
            'content': 'You should take this medication twice daily with food.',
            'userContext': {}
        }
    }
]

def run_tests():
    """Run all test cases"""
    print('🧪 Starting SAFEGUARD-Health API Tests (Python)\n')
    print('=' * 60)
    
    for test in test_cases:
        print(f"\n{test['name']}")
        print('-' * 60)
        
        try:
            response = requests.post(API_URL, json=test['data'], timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            print(f"✅ Decision: {data['decision']}")
            print(f"📊 Severity: {data['severity']}")
            print(f"💬 Explanation: {data['explanation']}")
            
            if data['details']['evidence_summary']:
                print(f"🔍 Evidence Analysis:")
                for e in data['details']['evidence_summary']:
                    claim_preview = e['claim'][:60] + '...' if len(e['claim']) > 60 else e['claim']
                    print(f"\n   📝 Claim: {claim_preview}")
                    print(f"   ✔️  Status: {e['status']}")
                    print(f"   🎯 Confidence: {e.get('confidence_level', 'UNKNOWN')}")
                    
                    if e.get('fallback_applied'):
                        print(f"   ⚠️  Note: Search fallback was applied (limited results)")
                    
                    # Show tier breakdown
                    tier_breakdown = e.get('tier_breakdown', {})
                    if any(tier_breakdown.values()):
                        print(f"   📊 Source Distribution:")
                        if tier_breakdown.get('government_who', 0) > 0:
                            print(f"      • Government/WHO: {tier_breakdown['government_who']}")
                        if tier_breakdown.get('peer_reviewed_medical', 0) > 0:
                            print(f"      • Peer-Reviewed/Medical: {tier_breakdown['peer_reviewed_medical']}")
                        if tier_breakdown.get('credible_health_info', 0) > 0:
                            print(f"      • Credible Health Info: {tier_breakdown['credible_health_info']}")
                        if tier_breakdown.get('untrusted', 0) > 0:
                            print(f"      • Untrusted: {tier_breakdown['untrusted']}")
                    
                    # Show Tier 1 sources first (PRIORITIZED)
                    if e.get('tier1_sources'):
                        print(f"   🏛️  TIER 1 - Government/WHO Sources:")
                        for source in e['tier1_sources']:
                            print(f"      • {source.get('title', 'Unknown')}")
                            print(f"        {source.get('url', 'No URL')}")
                            print(f"        Confidence: {source.get('confidence', 0)}%")
                    
                    # Show Tier 2 sources (Research/Medical)
                    if e.get('tier2_sources'):
                        print(f"   🏥 TIER 2 - Research/Medical Institutions:")
                        for source in e['tier2_sources']:
                            print(f"      • {source.get('title', 'Unknown')}")
                            print(f"        {source.get('url', 'No URL')}")
                            print(f"        Confidence: {source.get('confidence', 0)}%")
                    
                    # Show Tier 3 sources (Patient Info)
                    if e.get('tier3_sources'):
                        print(f"   📚 TIER 3 - Patient Information:")
                        for source in e['tier3_sources']:
                            print(f"      • {source.get('title', 'Unknown')}")
                            print(f"        {source.get('url', 'No URL')}")
                            print(f"        Confidence: {source.get('confidence', 0)}%")
                    
                    if not any([e.get('tier1_sources'), e.get('tier2_sources'), e.get('tier3_sources')]):
                        print(f"   ⚠️  No trusted sources found")
                    print()
        
        except requests.exceptions.RequestException as e:
            print(f"❌ Error: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"   Response: {e.response.text}")
    
    print('\n' + '=' * 60)
    print('✅ Tests completed\n')

if __name__ == '__main__':
    # Check if server is running
    try:
        health_response = requests.get('http://localhost:3000/health', timeout=5)
        print(f"✅ Server is running: {health_response.json()}\n")
        run_tests()
    except requests.exceptions.RequestException:
        print('❌ Error: Server is not running!')
        print('Please start the server first with: python app.py\n')