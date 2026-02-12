#!/usr/bin/env python3
"""
E2E Test: Visualization on Generate Feature

Tests that when outfits are generated (streaming endpoint), visualization
automatically starts and appears on the reveal page.

Expected flow:
1. Navigate to homepage
2. Click to generate outfits (occasion selection)
3. On reveal page, verify:
   - Outfit cards appear with collage images
   - "Creating your styled look..." spinner appears
   - Progress bar shows
   - After ~15-30s, visualization image appears (or timeout gracefully)

4. Check network for:
   - /api/visualization/status/{viz_key} polling every 3s
   - SSE response includes viz_key and viz_pending: true
"""

import asyncio
import json
import sys
from datetime import datetime

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("ERROR: playwright not installed. Run: pip install playwright && playwright install chromium")
    sys.exit(1)


async def test_visualization_on_generate():
    """Run the E2E test for visualization-on-generate feature."""

    results = {
        "timestamp": datetime.now().isoformat(),
        "url": "https://styleinspo.vercel.app/?user=peichin",
        "tests": {},
        "network_logs": [],
        "console_logs": [],
        "screenshots": []
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 390, 'height': 844},  # iPhone 14 dimensions
            user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15'
        )
        page = await context.new_page()

        # Capture network requests
        viz_status_requests = []
        sse_events = []

        async def handle_request(request):
            if '/visualization/status/' in request.url:
                viz_status_requests.append({
                    'url': request.url,
                    'timestamp': datetime.now().isoformat()
                })

        async def handle_response(response):
            if '/visualization/status/' in response.url:
                try:
                    body = await response.json()
                    viz_status_requests[-1]['response'] = body
                except:
                    pass

        page.on('request', handle_request)
        page.on('response', handle_response)

        # Capture console logs
        console_logs = []
        def handle_console(msg):
            console_logs.append({
                'type': msg.type,
                'text': msg.text,
                'timestamp': datetime.now().isoformat()
            })
        page.on('console', handle_console)

        try:
            # Step 1: Navigate to homepage
            print("\n=== Step 1: Navigate to homepage ===")
            await page.goto('https://styleinspo.vercel.app/?user=peichin', wait_until='networkidle')
            await page.screenshot(path='.playwright-mcp/viz_e2e_01_homepage.png')
            results['screenshots'].append('viz_e2e_01_homepage.png')
            print("Homepage loaded")

            # Step 2: Click "Plan my outfit" button
            print("\n=== Step 2: Click 'Plan my outfit' button ===")

            # Wait for hydration
            await asyncio.sleep(3)

            # Try multiple approaches to click the button
            button_clicked = False

            # Approach 1: Click by text
            try:
                await page.click('text="Plan my outfit"', timeout=5000)
                button_clicked = True
                print("Clicked 'Plan my outfit' button (text selector)")
            except Exception as e1:
                print(f"Approach 1 failed: {e1}")

                # Approach 2: Click by role with name
                try:
                    await page.get_by_role('button', name='Plan my outfit').click(timeout=5000)
                    button_clicked = True
                    print("Clicked 'Plan my outfit' button (role selector)")
                except Exception as e2:
                    print(f"Approach 2 failed: {e2}")

                    # Approach 3: Click the visible terracotta button (bg-terracotta)
                    try:
                        buttons = await page.locator('.bg-terracotta').all()
                        if buttons:
                            await buttons[0].click()
                            button_clicked = True
                            print("Clicked first bg-terracotta button")
                    except Exception as e3:
                        print(f"Approach 3 failed: {e3}")

            if button_clicked:
                results['tests']['find_generate_button'] = {'passed': True}
                await asyncio.sleep(1)
                await page.screenshot(path='.playwright-mcp/viz_e2e_02_after_click.png')
                results['screenshots'].append('viz_e2e_02_after_click.png')
            else:
                results['tests']['find_generate_button'] = {'passed': False, 'error': 'Could not click button'}
                await page.screenshot(path='.playwright-mcp/viz_e2e_02_no_click.png')
                results['screenshots'].append('viz_e2e_02_no_click.png')
                print("ERROR: Could not click generate button")

            # Step 3: Handle occasion selection
            print("\n=== Step 3: Handle occasion selection ===")
            await asyncio.sleep(2)
            current_url = page.url
            print(f"Current URL: {current_url}")
            await page.screenshot(path='.playwright-mcp/viz_e2e_03_occasion.png')
            results['screenshots'].append('viz_e2e_03_occasion.png')

            # Click on an occasion (the buttons are pill-shaped with text)
            occasion_clicked = False
            occasion_options = [
                'Working from home',
                'Business meeting',
                'Weekend errands',
                'Coffee meeting',
                'Brunch',
                'School drop-off'
            ]

            for occasion in occasion_options:
                try:
                    await page.click(f'text="{occasion}"', timeout=2000)
                    print(f"Selected '{occasion}' occasion")
                    occasion_clicked = True
                    break
                except:
                    continue

            if not occasion_clicked:
                print("WARNING: Could not select any occasion")

            # Take screenshot after selecting occasion
            await asyncio.sleep(0.5)
            await page.screenshot(path='.playwright-mcp/viz_e2e_03a_occasion_selected.png')
            results['screenshots'].append('viz_e2e_03a_occasion_selected.png')

            # Click "Create Outfits" button
            try:
                await page.click('text="Create Outfits"', timeout=5000)
                print("Clicked 'Create Outfits' button")
            except:
                try:
                    # Try clicking the terracotta button directly
                    await page.locator('.bg-terracotta').click(timeout=3000)
                    print("Clicked terracotta create button")
                except Exception as e:
                    print(f"WARNING: Could not click create button: {e}")

            # Step 4: Wait for outfit generation
            print("\n=== Step 4: Wait for outfit generation ===")
            await asyncio.sleep(3)
            current_url = page.url
            print(f"Current URL: {current_url}")
            await page.screenshot(path='.playwright-mcp/viz_e2e_04_generating.png')
            results['screenshots'].append('viz_e2e_04_generating.png')

            # Wait for outfit cards to appear (h2 with "Outfit X")
            try:
                await page.wait_for_selector('text="Outfit 1"', timeout=90000)
                print("Outfit 1 appeared!")
                results['tests']['outfits_appear'] = {'passed': True}
                await page.screenshot(path='.playwright-mcp/viz_e2e_04a_outfit_appeared.png')
                results['screenshots'].append('viz_e2e_04a_outfit_appeared.png')
            except Exception as e:
                print(f"ERROR: Outfits did not appear: {e}")
                results['tests']['outfits_appear'] = {'passed': False, 'error': str(e)}
                await page.screenshot(path='.playwright-mcp/viz_e2e_04a_timeout.png')
                results['screenshots'].append('viz_e2e_04a_timeout.png')

            # Step 5: Check for visualization spinner
            print("\n=== Step 5: Check for visualization spinner ===")

            # Look for the spinner text or progress bar
            spinner_found = False
            try:
                spinner = page.locator('text="Creating your styled look"')
                if await spinner.count() > 0:
                    spinner_found = True
                    print("Found 'Creating your styled look' text")
            except:
                pass

            if not spinner_found:
                # Check for progress bar
                try:
                    progress = page.locator('.bg-terracotta.h-1, .bg-terracotta.h-1\\.5')
                    count = await progress.count()
                    if count > 0:
                        spinner_found = True
                        print(f"Found {count} progress bar(s)")
                except:
                    pass

            if spinner_found:
                results['tests']['visualization_spinner'] = {'passed': True}
                await page.screenshot(path='.playwright-mcp/viz_e2e_05_spinner.png')
                results['screenshots'].append('viz_e2e_05_spinner.png')
            else:
                results['tests']['visualization_spinner'] = {
                    'passed': False,
                    'error': 'Spinner not found - viz may not have started automatically'
                }
                print("WARNING: Visualization spinner not found")

            # Step 6: Wait and check for viz polling
            print("\n=== Step 6: Wait for visualization polling ===")
            print("Waiting 20 seconds to capture viz polling...")
            await asyncio.sleep(20)

            await page.screenshot(path='.playwright-mcp/viz_e2e_06_after_wait.png')
            results['screenshots'].append('viz_e2e_06_after_wait.png')

            # Check for viz status requests
            results['network_logs'] = viz_status_requests
            print(f"Captured {len(viz_status_requests)} viz status requests")

            if viz_status_requests:
                results['tests']['viz_polling'] = {
                    'passed': True,
                    'request_count': len(viz_status_requests),
                    'sample': viz_status_requests[:5]
                }
                print("Viz polling confirmed:")
                for req in viz_status_requests[:5]:
                    print(f"  {req.get('url', 'no url')}")
                    if 'response' in req:
                        print(f"    Response: {req['response']}")
            else:
                results['tests']['viz_polling'] = {
                    'passed': False,
                    'error': 'No viz status polling requests captured'
                }
                print("WARNING: No viz polling requests detected")

            # Step 7: Check for visualization completion
            print("\n=== Step 7: Check for visualization completion ===")
            print("Waiting 25 more seconds for viz completion...")
            await asyncio.sleep(25)

            await page.screenshot(path='.playwright-mcp/viz_e2e_07_final.png')
            results['screenshots'].append('viz_e2e_07_final.png')

            # Scroll down to see more content
            await page.evaluate('window.scrollBy(0, 600)')
            await asyncio.sleep(1)
            await page.screenshot(path='.playwright-mcp/viz_e2e_07a_scrolled.png')
            results['screenshots'].append('viz_e2e_07a_scrolled.png')

            # Check for "Tap to expand" which indicates viz image loaded
            tap_badges = await page.locator('text="Tap to expand"').all()
            if tap_badges:
                results['tests']['visualization_complete'] = {
                    'passed': True,
                    'count': len(tap_badges)
                }
                print(f"Found {len(tap_badges)} visualization images (Tap to expand badges)")
            else:
                # Check for viz images directly
                viz_images = await page.locator('img[src*="visualization"]').all()
                if viz_images:
                    results['tests']['visualization_complete'] = {
                        'passed': True,
                        'count': len(viz_images)
                    }
                    print(f"Found {len(viz_images)} visualization images")
                else:
                    # Check if still showing spinner (still generating)
                    still_generating = await page.locator('text="Creating your styled look"').count()
                    if still_generating > 0:
                        results['tests']['visualization_complete'] = {
                            'passed': False,
                            'note': 'Still generating after timeout'
                        }
                        print("Visualization still generating (timeout)")
                    else:
                        # Check for error state
                        errors = await page.locator('.text-red-500, .text-red-600, .bg-red-50').count()
                        if errors > 0:
                            results['tests']['visualization_complete'] = {
                                'passed': False,
                                'error': 'Visualization failed with error'
                            }
                            print("Visualization error state found")
                        else:
                            results['tests']['visualization_complete'] = {
                                'passed': False,
                                'note': 'No visualization images or spinners found'
                            }
                            print("No visualization found")

            # Final summary of network calls
            print(f"\n=== Network Summary ===")
            print(f"Total viz status requests: {len(viz_status_requests)}")
            if viz_status_requests:
                # Check last response status
                last = viz_status_requests[-1]
                if 'response' in last:
                    print(f"Last response: {last['response']}")

            # Collect console logs
            results['console_logs'] = console_logs
            error_logs = [log for log in console_logs if log['type'] == 'error']
            if error_logs:
                print(f"\nConsole errors: {len(error_logs)}")
                for err in error_logs[:5]:
                    print(f"  {err['text'][:100]}")

        except Exception as e:
            print(f"\nERROR during test: {e}")
            results['error'] = str(e)
            import traceback
            traceback.print_exc()
            await page.screenshot(path='.playwright-mcp/viz_e2e_error.png')
            results['screenshots'].append('viz_e2e_error.png')

        finally:
            await browser.close()

    # Save results
    results_path = '.playwright-mcp/viz_e2e_results.json'
    with open(results_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {results_path}")

    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    for test_name, result in results.get('tests', {}).items():
        status = "PASS" if result.get('passed') else "FAIL"
        print(f"  {test_name}: {status}")
        if not result.get('passed'):
            if result.get('error'):
                print(f"    Error: {result['error']}")
            if result.get('note'):
                print(f"    Note: {result['note']}")
    print("="*60)

    return results


if __name__ == '__main__':
    results = asyncio.run(test_visualization_on_generate())
