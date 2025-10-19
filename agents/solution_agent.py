"""
Solution Agent - AI-Powered Network Problem Solver
Uses LLM to generate creative, context-aware solutions based on diagnostic results
"""

import json
from datetime import datetime
from typing import Dict, List

from crewai import Agent, Task, Crew, LLM
from crewai.tools import tool


# ============================================================================
# TOOLS - Solution generation helpers
# ============================================================================

@tool("get_common_solutions")
def get_common_solutions(issue_type: str) -> str:
    """
    Get common solutions for specific network issue types.
    
    Args:
        issue_type: Type of network issue (high_latency, weak_signal, dns_issues, etc.)
    
    Returns:
        JSON string with categorized solutions for the issue type
    """
    solution_database = {
        'high_latency': {
            'quick_fixes': [
                'Restart router by unplugging for 30 seconds',
                'Move closer to WiFi router if using wireless',
                'Close bandwidth-heavy applications',
                'Test with ethernet cable to rule out WiFi issues'
            ],
            'intermediate': [
                'Check number of connected devices on network',
                'Switch to 5GHz WiFi band if available',
                'Update router firmware',
                'Check for ISP outages on status page'
            ],
            'advanced': [
                'Enable QoS (Quality of Service) on router',
                'Contact ISP about line quality',
                'Upgrade router if 5+ years old',
                'Consider upgrading internet plan'
            ]
        },
        'weak_signal': {
            'quick_fixes': [
                'Move closer to router immediately',
                'Ensure router antennas are upright',
                'Remove metal objects between device and router',
                'Elevate router off the floor'
            ],
            'intermediate': [
                'Reposition router to central location in home',
                'Switch to 2.4GHz for better range (if on 5GHz)',
                'Check for interference from microwaves/baby monitors',
                'Update WiFi drivers on your device'
            ],
            'advanced': [
                'Install WiFi extender or mesh system',
                'Upgrade to router with better antennas',
                'Use powerline ethernet adapters',
                'Run ethernet cable if feasible'
            ]
        },
        'dns_issues': {
            'quick_fixes': [
                'Change DNS to Google DNS: 8.8.8.8, 8.8.4.4',
                'Change DNS to Cloudflare: 1.1.1.1, 1.0.0.1',
                'Flush DNS cache: sudo systemd-resolve --flush-caches',
                'Restart network service'
            ],
            'intermediate': [
                'Configure DNS servers in router settings',
                'Test multiple DNS providers for speed',
                'Check /etc/resolv.conf for correct DNS entries',
                'Disable IPv6 if causing conflicts'
            ],
            'advanced': [
                'Set up local DNS caching with dnsmasq',
                'Use DNS-over-HTTPS (DoH) for privacy',
                'Configure backup DNS servers',
                'Monitor DNS performance with tools'
            ]
        },
        'router_issues': {
            'quick_fixes': [
                'Reboot router (unplug 30 seconds)',
                'Check all cables are firmly connected',
                'Ensure router has ventilation (not overheating)',
                'Check router status lights for errors'
            ],
            'intermediate': [
                'Update router firmware from admin panel',
                'Review router logs for error messages',
                'Disable unused router features',
                'Reset router to factory defaults (backup first)'
            ],
            'advanced': [
                'Monitor router CPU/temperature',
                'Replace router if hardware failing',
                'Install custom firmware (DD-WRT/OpenWrt)',
                'Set up backup router'
            ]
        },
        'interference': {
            'quick_fixes': [
                'Move router away from microwave and cordless phones',
                'Switch to 5GHz band (less interference)',
                'Turn off unused 2.4GHz devices temporarily',
                'Change WiFi channel in router settings'
            ],
            'intermediate': [
                'Scan WiFi channels and pick least congested',
                'Enable 20MHz channel width instead of 40MHz',
                'Use WiFi analyzer to find interference sources',
                'Coordinate with neighbors on channel usage'
            ],
            'advanced': [
                'Install directional antennas',
                'Deploy mesh WiFi with band steering',
                'Upgrade to WiFi 6 (better interference handling)',
                'Use wired backhaul for mesh nodes'
            ]
        },
        'isp_issues': {
            'quick_fixes': [
                'Check ISP status page for outages',
                'Restart ISP modem',
                'Test at different times of day',
                'Document issue patterns with timestamps'
            ],
            'intermediate': [
                'Contact ISP tech support with latency data',
                'Request line quality check from ISP',
                'Check service agreement for guaranteed speeds',
                'Test with mobile hotspot to confirm ISP issue'
            ],
            'advanced': [
                'File formal complaint with ISP',
                'Document issue over time for evidence',
                'Consider switching ISP providers',
                'Contact telecommunications authority if unresolved'
            ]
        }
    }
    
    # Match issue type to database
    issue_lower = issue_type.lower().replace('_', '')
    
    for db_key, solutions in solution_database.items():
        if db_key.replace('_', '') in issue_lower or issue_lower in db_key.replace('_', ''):
            return json.dumps({
                'issue_type': issue_type,
                'found': True,
                'solutions': solutions
            })
    
    # Return general solutions if no match
    return json.dumps({
        'issue_type': issue_type,
        'found': False,
        'solutions': {
            'quick_fixes': [
                'Restart router and modem',
                'Test with ethernet cable',
                'Check for software updates',
                'Monitor issue over time'
            ],
            'intermediate': [
                'Contact ISP or network admin',
                'Run extended diagnostics',
                'Check hardware for failures'
            ],
            'advanced': [
                'Consider professional network assessment',
                'Upgrade network hardware',
                'Implement network monitoring'
            ]
        }
    })


@tool("prioritize_solutions")
def prioritize_solutions(solutions_list: str) -> str:
    """
    Prioritize solutions based on effort and impact.
    
    Args:
        solutions_list: JSON string with list of solutions to prioritize
    
    Returns:
        JSON string with solutions sorted by priority (high to low)
    """
    try:
        solutions = json.loads(solutions_list)
        
        # Simple prioritization logic based on keywords
        priority_scores = {}
        
        for i, solution in enumerate(solutions):
            score = 0
            solution_lower = solution.lower()
            
            # High priority (quick wins)
            if any(word in solution_lower for word in ['restart', 'reboot', 'check', 'move', 'switch']):
                score += 10
            
            # Medium priority
            if any(word in solution_lower for word in ['update', 'change', 'configure', 'contact']):
                score += 5
            
            # Lower priority (time-consuming)
            if any(word in solution_lower for word in ['upgrade', 'replace', 'install', 'consider']):
                score += 2
            
            priority_scores[i] = score
        
        # Sort by score descending
        sorted_indices = sorted(priority_scores.keys(), key=lambda x: priority_scores[x], reverse=True)
        prioritized = [solutions[i] for i in sorted_indices]
        
        return json.dumps({
            'prioritized_solutions': prioritized,
            'total': len(prioritized)
        })
        
    except Exception as e:
        return json.dumps({
            'error': str(e),
            'prioritized_solutions': [],
            'total': 0
        })


@tool("estimate_resolution_time")
def estimate_resolution_time(solution: str) -> str:
    """
    Estimate how long a solution will take to implement.
    
    Args:
        solution: Description of the solution
    
    Returns:
        JSON string with time estimate
    """
    solution_lower = solution.lower()
    
    # Quick actions (< 5 mins)
    if any(word in solution_lower for word in ['restart', 'reboot', 'check', 'move', 'switch']):
        return json.dumps({
            'solution': solution,
            'estimated_time': '1-5 minutes',
            'category': 'quick'
        })
    
    # Medium actions (5-20 mins)
    elif any(word in solution_lower for word in ['update', 'change', 'configure', 'scan', 'test']):
        return json.dumps({
            'solution': solution,
            'estimated_time': '5-20 minutes',
            'category': 'moderate'
        })
    
    # Long actions (20+ mins)
    elif any(word in solution_lower for word in ['upgrade', 'replace', 'install', 'contact']):
        return json.dumps({
            'solution': solution,
            'estimated_time': '20-60 minutes',
            'category': 'extensive'
        })
    
    else:
        return json.dumps({
            'solution': solution,
            'estimated_time': '10-30 minutes',
            'category': 'moderate'
        })


# ============================================================================
# SOLUTION AGENT CLASS
# ============================================================================

class SolutionAgent:
    """
    AI-Powered Solution Agent using LLM
    Generates creative, context-aware solutions for network issues
    """
    
    def __init__(self, llm: LLM):
        """
        Initialize Solution Agent with LLM
        
        Args:
            llm: Language model for the agent
        """
        self.llm = llm
        
        # Create the CrewAI agent (NO TOOLS - simpler for small models)
        self.agent = Agent(
            role='Network Solutions Specialist',
            goal='Provide 3-5 practical quick fixes for network problems',
            backstory="""You are a helpful network technician. You give simple, clear instructions.
            You focus on quick fixes that anyone can do. You are brief and practical.""",
            tools=[],  # NO TOOLS - keeps it simple for small models
            verbose=True,
            llm=llm,
            max_iter=1  # Only one iteration for speed
        )
        
        print(f"✅ AI Solution Agent initialized with LLM: {llm.model}")
    
    def _get_solution_template(self, issue_type: str) -> str:
        """Get common solutions as text (no tools needed)"""
        templates = {
            'high_local_network_latency': """
  - Restart router (unplug 30 seconds, plug back in)
  - Move closer to WiFi router
  - Check how many devices are connected
  - Switch to 5GHz WiFi band if available
  - Update router firmware""",
            'high_external_latency': """
  - Test with ethernet cable to rule out WiFi
  - Restart modem and router
  - Contact ISP about latency issues
  - Check ISP status page for outages
  - Try different DNS servers (8.8.8.8)""",
            'moderate_network_degradation': """
  - Move closer to WiFi router
  - Restart WiFi adapter
  - Switch to less congested WiFi channel
  - Remove obstacles between you and router
  - Use 5GHz instead of 2.4GHz""",
            'weak_wifi_signal': """
  - Move closer to router immediately
  - Ensure router antennas are upright
  - Reposition router to central location
  - Switch to 2.4GHz for better range
  - Remove metal objects blocking signal"""
        }
        
        # Match issue type
        issue_lower = issue_type.lower().replace('_', '')
        for key, template in templates.items():
            if key.replace('_', '') in issue_lower or issue_lower in key.replace('_', ''):
                return template
        
        # Default template
        return """
  - Restart router and modem
  - Test with ethernet cable
  - Check WiFi signal strength
  - Update router firmware
  - Contact ISP support"""
    
    def create_solution_task(self, diagnosis: Dict) -> Task:
        """
        Create a simplified task for small LLMs
        
        Args:
            diagnosis: Diagnosis dictionary from Diagnostic Agent
            
        Returns:
            CrewAI Task
        """
        primary_issue = diagnosis.get('primary_issue', 'unknown')
        root_cause = diagnosis.get('root_cause', 'Unknown cause')
        diagnostic_recs = diagnosis.get('recommendations', [])
        
        # Create simple recommendation list
        recs_text = "\n".join([f"  {i+1}. {r}" for i, r in enumerate(diagnostic_recs[:3])]) if diagnostic_recs else "  No specific recommendations"
        
        # Get common solutions based on issue type
        common_solutions = self._get_solution_template(primary_issue)
        
        return Task(
            description=f"""Network problem: {root_cause}

Here are common solutions for this issue:
{common_solutions}

Diagnostic recommendations:
{recs_text}

YOUR TASK: List 5 specific actions to fix this, in priority order.
Start with quickest/easiest fixes first.

Format your answer as:
1. [Action with brief explanation]
2. [Action with brief explanation]
3. [Action with brief explanation]
4. [Action with brief explanation]
5. [Action with brief explanation]

Be specific and actionable. Keep each item to one sentence.""",
            agent=self.agent,
            expected_output="A numbered list of 5 specific actions to fix the network issue"
        )
    
    def generate_solutions(self, diagnosis: Dict) -> Dict:
        """
        Generate AI-powered solutions using LLM
        
        Args:
            diagnosis: Diagnosis dictionary from Diagnostic Agent
            
        Returns:
            Solution report with AI-generated recommendations
        """
        print(f"\n💡 AI Solution Agent analyzing diagnosis...")
        print(f"📊 Issue: {diagnosis.get('primary_issue', 'unknown')}")
        print(f"🎯 Root Cause: {diagnosis.get('root_cause', 'Unknown')[:60]}...")
        
        # Check if network is healthy - no solutions needed!
        if diagnosis.get('primary_issue') == 'network_healthy':
            print("\n✅ Network is healthy - no solutions needed!")
            return {
                'timestamp': datetime.now().isoformat(),
                'diagnosis_summary': {
                    'issue': diagnosis.get('primary_issue'),
                    'root_cause': diagnosis.get('root_cause'),
                    'confidence': diagnosis.get('confidence')
                },
                'solutions': {
                    'solutions_list': [
                        'Network is performing well - no action needed',
                        'Continue monitoring for any changes',
                        'Run diagnostics again if you notice slowdowns'
                    ],
                    'note': 'Network is healthy'
                },
                'generated_by': 'Solution Agent',
                'llm_model': self.llm.model
            }
        
        # Create task
        task = self.create_solution_task(diagnosis)
        
        # Create crew with just the solution agent
        crew = Crew(
            agents=[self.agent],
            tasks=[task],
            verbose=True
        )
        
        # Execute the crew with progress indicator
        print("\n🤖 Engaging AI Solution Agent...")
        
        import threading
        import time
        
        # Progress indicator thread
        stop_progress = threading.Event()
        def show_progress():
            dots = 0
            while not stop_progress.is_set():
                time.sleep(3)
                if not stop_progress.is_set():
                    dots = (dots + 1) % 4
                    print(f"   ⏳ AI thinking{'.' * (dots + 1)}")
        
        progress_thread = threading.Thread(target=show_progress, daemon=True)
        progress_thread.start()
        
        try:
            result = crew.kickoff()
        finally:
            # Stop progress indicator
            stop_progress.set()
            progress_thread.join(timeout=0.1)
        
        # Parse the simple text result
        result_text = str(result).strip()
        print(f"\n📝 AI Response received ({len(result_text)} chars)")
        
        # Extract numbered list from response
        solutions_list = []
        for line in result_text.split('\n'):
            line = line.strip()
            # Look for numbered items like "1. ", "2. ", etc.
            if line and len(line) > 3 and line[0].isdigit() and line[1] in ['.', ')', ':']:
                # Remove the number prefix
                solution = line[line.find(' ')+1:].strip()
                if solution:
                    solutions_list.append(solution)
        
        # If we got at least 3 solutions, use them
        if len(solutions_list) >= 3:
            print(f"✅ Extracted {len(solutions_list)} solutions from AI")
            solution_data = {
                'solutions_list': solutions_list,
                'raw_response': result_text[:500]  # First 500 chars
            }
        else:
            # Fallback if parsing failed
            print(f"⚠️  Could not parse numbered list, using template solutions")
            solution_data = {
                'solutions_list': [
                    'Restart your router by unplugging it for 30 seconds',
                    'Move closer to the WiFi router to improve signal',
                    'Check how many devices are connected to your network',
                    'Test connection with an ethernet cable if possible',
                    'Update router firmware from the admin panel'
                ],
                'raw_response': result_text[:500],
                'note': 'Using template solutions'
            }
        
        # Add metadata
        solution_report = {
            'timestamp': datetime.now().isoformat(),
            'diagnosis_summary': {
                'issue': diagnosis.get('primary_issue'),
                'root_cause': diagnosis.get('root_cause'),
                'confidence': diagnosis.get('confidence')
            },
            'solutions': solution_data,
            'generated_by': 'AI Solution Agent',
            'llm_model': self.llm.model
        }
        
        return solution_report
    
    def print_solutions(self, solution_report: Dict):
        """
        Print AI-generated solutions in simple format
        """
        print("\n" + "="*70)
        print("💡 AI-GENERATED SOLUTIONS")
        print("="*70)
        
        diagnosis = solution_report.get('diagnosis_summary', {})
        print(f"\n📊 Issue: {diagnosis.get('issue', 'Unknown')}")
        print(f"🎯 Root Cause: {diagnosis.get('root_cause', 'Unknown')}")
        print(f"🤖 Generated by: {solution_report.get('llm_model', 'AI')}")
        
        solutions = solution_report.get('solutions', {})
        solutions_list = solutions.get('solutions_list', [])
        
        if solutions_list:
            print(f"\n⚡ RECOMMENDED ACTIONS (Try in order):")
            print("="*70)
            for i, solution in enumerate(solutions_list, 1):
                print(f"\n{i}. {solution}")
            
            # Estimate timing
            total = len(solutions_list)
            if total >= 5:
                print(f"\n⏱️  Estimated time: 15-30 minutes for all steps")
            elif total >= 3:
                print(f"\n⏱️  Estimated time: 10-20 minutes for all steps")
            else:
                print(f"\n⏱️  Estimated time: 5-15 minutes")
        
        # Show note if present
        if solutions.get('note'):
            print(f"\n💭 Note: {solutions['note']}")
        
        print("\n" + "="*70)
        print("✅ Try each step and test your connection after each one!")
        print("="*70)


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='AI Solution Agent')
    parser.add_argument('--diagnosis-file', type=str,
                        help='Path to diagnosis JSON file')
    parser.add_argument('--model', default='ollama/qwen2.5:0.5b',
                        help='LLM model to use')
    
    args = parser.parse_args()
    
    # Initialize LLM
    try:
        llm = LLM(model=args.model, base_url="http://localhost:11434")
    except Exception as e:
        print(f"❌ Failed to initialize LLM: {e}")
        print("Make sure Ollama is running: ollama serve")
        sys.exit(1)
    
    # Initialize Solution Agent
    solution_agent = SolutionAgent(llm)
    
    # Load diagnosis
    if args.diagnosis_file:
        try:
            print(f"\n📁 Loading diagnosis from: {args.diagnosis_file}\n")
            with open(args.diagnosis_file, 'r') as f:
                diagnosis = json.load(f)
        except Exception as e:
            print(f"❌ Error loading diagnosis file: {e}")
            sys.exit(1)
    else:
        # Use sample diagnosis for testing
        print("\n🧪 Using sample diagnosis for testing\n")
        diagnosis = {
            'timestamp': datetime.now().isoformat(),
            'alert_status': 'degraded',
            'primary_issue': 'high_local_network_latency',
            'root_cause': 'Router latency is high (156ms), indicating local network congestion or WiFi issues',
            'confidence': 'high',
            'evidence': [
                'Router latency: 156ms (threshold: 50ms)',
                'WiFi signal is weak: -72dBm',
                '23 WiFi networks detected (congested environment)'
            ],
            'recommendations': [
                'Improve WiFi signal strength',
                'Check router CPU/memory usage',
                'Switch to less congested WiFi channel'
            ]
        }
    
    # Generate solutions
    solutions = solution_agent.generate_solutions(diagnosis)
    
    # Print solutions
    solution_agent.print_solutions(solutions)
    
    # Save to file
    output_file = '/tmp/ai_solutions.json'
    with open(output_file, 'w') as f:
        json.dump(solutions, f, indent=2)
    print(f"\n💾 Solutions saved to: {output_file}")
