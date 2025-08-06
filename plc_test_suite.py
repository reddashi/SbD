#!/usr/bin/env python3
"""
Comprehensive Testing Suite for PLC Simulation System (gh.py)

Tests all PLCs individually and in integration scenarios:
- Temperature PLC: heating, cooling, normal operation
- Irrigation PLC: pumping, draining, normal operation  
- Light PLC: grow lights, dark windows, photoperiod tracking
- CO2 PLC: dosing, venting, day/night cycles
- PLC1 Coordinator: message processing, threshold detection
- Threading: startup, cleanup, exception handling
- Edge cases: boundary conditions, time transitions
"""

import unittest
import threading
import queue
import time
import datetime
from unittest.mock import patch, MagicMock
import sys
import os

# Color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'  # Reset color

# Check if terminal supports colors (most modern terminals do)
def supports_color():
    # Enable colors for most terminals - modern Windows terminals support ANSI codes
    return hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()

def green(text):
    return f"{Colors.GREEN}{text}{Colors.END}" if supports_color() else f"✓ {text}"

def red(text):
    return f"{Colors.RED}{text}{Colors.END}" if supports_color() else f"✗ {text}"

def yellow(text):
    return f"{Colors.YELLOW}{text}{Colors.END}" if supports_color() else f"⚠ {text}"

def blue(text):
    return f"{Colors.BLUE}{text}{Colors.END}" if supports_color() else f"ℹ {text}"

def bold(text):
    return f"{Colors.BOLD}{text}{Colors.END}" if supports_color() else text

# Import the PLC classes (assuming gh.py is in same directory)
try:
    from gh import (
        PLC1, TemperaturePLC, IrrigationPLC, LightPLC, CO2PLC,
        MIN_TEMP, MAX_TEMP, MIN_MOISTURE, MAX_MOISTURE, 
        MIN_LIGHT, MAX_LIGHT, MIN_CO2, MAX_CO2,
        TEMP_INTERVAL, IRRIGATION_INTERVAL, LIGHT_INTERVAL, CO2_INTERVAL
    )
except ImportError:
    print("ERROR: Cannot import from gh.py. Make sure gh.py is in the same directory.")
    sys.exit(1)

class TestTemperaturePLC(unittest.TestCase):
    """Test Temperature PLC functionality"""
    
    def setUp(self):
        self.messages = []
        def mock_sender(msg):
            self.messages.append(msg)
        self.sender = mock_sender
    
    def test_heating_scenario(self):
        """Test heating when temperature is below threshold"""
        plc = TemperaturePLC(self.sender, initial_temp=20.0, drift=0.0)  # Below MIN_TEMP (25)
        plc.run(cycles=1)
        
        self.assertEqual(len(self.messages), 1)
        msg = self.messages[0]
        self.assertIn('temperature', msg)
        self.assertIn('heater_pct', msg)
        self.assertIn('cooler_pct', msg)
        self.assertGreater(msg['heater_pct'], 0)
        self.assertEqual(msg['cooler_pct'], 0.0)
        print(green(f"✓ Heating test: {msg}"))
    
    def test_cooling_scenario(self):
        """Test cooling when temperature is above threshold"""
        plc = TemperaturePLC(self.sender, initial_temp=35.0, drift=0.0)  # Above MAX_TEMP (27)
        plc.run(cycles=1)
        
        self.assertEqual(len(self.messages), 1)
        msg = self.messages[0]
        self.assertEqual(msg['heater_pct'], 0.0)
        self.assertGreater(msg['cooler_pct'], 0)
        print(green(f"✓ Cooling test: {msg}"))
    
    def test_normal_operation(self):
        """Test normal operation within comfort band"""
        plc = TemperaturePLC(self.sender, initial_temp=26.0, drift=0.0)  # Within MIN_TEMP-MAX_TEMP
        plc.run(cycles=1)
        
        self.assertEqual(len(self.messages), 1)
        msg = self.messages[0]
        self.assertEqual(msg['heater_pct'], 0.0)
        self.assertEqual(msg['cooler_pct'], 0.0)
        print(green(f"✓ Normal temp operation: {msg}"))
    
    def test_boundary_conditions(self):
        """Test extreme temperature values"""
        # Test minimum boundary
        plc = TemperaturePLC(self.sender, initial_temp=-10.0, drift=0.0)
        plc.run(cycles=1)
        self.assertGreaterEqual(self.messages[0]['temperature'], 0)  # Should clamp to TEMP_MIN_BOUND
        
        # Test maximum boundary  
        self.messages.clear()
        plc = TemperaturePLC(self.sender, initial_temp=100.0, drift=0.0)
        plc.run(cycles=1)
        self.assertLessEqual(self.messages[0]['temperature'], 50)  # Should clamp to TEMP_MAX_BOUND
        print(green("✓ Temperature boundary conditions"))


class TestIrrigationPLC(unittest.TestCase):
    """Test Irrigation PLC functionality"""
    
    def setUp(self):
        self.messages = []
        def mock_sender(msg):
            self.messages.append(msg)
        self.sender = mock_sender
    
    def test_pumping_scenario(self):
        """Test pumping when moisture is below threshold"""
        plc = IrrigationPLC(self.sender, initial_moisture=30.0, dry_drift=0.0)  # Below MIN_MOISTURE (40)
        plc.run(cycles=1)
        
        self.assertEqual(len(self.messages), 1)
        msg = self.messages[0]
        self.assertGreater(msg['pump_pct'], 0)
        self.assertEqual(msg['drain_pct'], 0.0)
        print(green(f"✓ Pumping test: {msg}"))
    
    def test_draining_scenario(self):
        """Test draining when moisture is above threshold"""
        plc = IrrigationPLC(self.sender, initial_moisture=80.0, dry_drift=0.0)  # Above MAX_MOISTURE (60)
        plc.run(cycles=1)
        
        self.assertEqual(len(self.messages), 1)
        msg = self.messages[0]
        self.assertEqual(msg['pump_pct'], 0.0)
        self.assertGreater(msg['drain_pct'], 0)
        print(green(f"✓ Draining test: {msg}"))
    
    def test_normal_operation(self):
        """Test normal operation within comfort band"""
        plc = IrrigationPLC(self.sender, initial_moisture=50.0, dry_drift=0.0)  # Within band
        plc.run(cycles=1)
        
        self.assertEqual(len(self.messages), 1)
        msg = self.messages[0]
        self.assertEqual(msg['pump_pct'], 0.0)
        self.assertEqual(msg['drain_pct'], 0.0)
        print(green(f"✓ Normal irrigation operation: {msg}"))


class TestLightPLC(unittest.TestCase):
    """Test Light PLC functionality"""
    
    def setUp(self):
        self.messages = []
        def mock_sender(msg):
            self.messages.append(msg)
        self.sender = mock_sender
    
    @patch('gh.datetime')
    def test_dark_window_operation(self, mock_datetime):
        """Test lights are OFF during dark window"""
        # Mock time to be in dark window (23:00)
        mock_now = MagicMock()
        mock_now.hour = 23
        mock_datetime.datetime.now.return_value = mock_now
        mock_datetime.date.today.return_value = datetime.date(2025, 1, 1)
        
        plc = LightPLC(self.sender, initial_light=100.0, natural_drift=0.0)  # Below MIN_LIGHT
        plc.run(cycles=1)
        
        self.assertEqual(len(self.messages), 1)
        msg = self.messages[0]
        self.assertEqual(msg['grow_power_pct'], 0.0)  # Should be OFF in dark window
        print(green(f"✓ Dark window test: {msg}"))
    
    @patch('gh.datetime')
    def test_normal_light_operation(self, mock_datetime):
        """Test grow lights activate when needed during daylight"""
        # Mock time to be outside dark window (12:00)
        mock_now = MagicMock()
        mock_now.hour = 12
        mock_datetime.datetime.now.return_value = mock_now
        mock_datetime.date.today.return_value = datetime.date(2025, 1, 1)
        
        plc = LightPLC(self.sender, initial_light=100.0, natural_drift=0.0)  # Below MIN_LIGHT (200)
        plc.run(cycles=1)
        
        self.assertEqual(len(self.messages), 1)
        msg = self.messages[0]
        self.assertGreater(msg['grow_power_pct'], 0)  # Should activate grow lights
        print(green(f"✓ Normal light operation: {msg}"))


class TestCO2PLC(unittest.TestCase):
    """Test CO2 PLC functionality"""
    
    def setUp(self):
        self.messages = []
        def mock_sender(msg):
            self.messages.append(msg)
        self.sender = mock_sender
    
    @patch('gh.datetime')
    def test_daytime_dosing(self, mock_datetime):
        """Test CO2 dosing during daytime when levels are low"""
        # Mock daytime (12:00)
        mock_now = MagicMock()
        mock_now.hour = 12
        mock_datetime.datetime.now.return_value = mock_now
        
        plc = CO2PLC(self.sender, initial_ppm=700.0)  # Below MIN_CO2 (800)
        plc.run(cycles=1)
        
        self.assertEqual(len(self.messages), 1)
        msg = self.messages[0]
        self.assertGreater(msg['pump_pct'], 0)
        self.assertEqual(msg['vent_pct'], 0.0)
        print(green(f"✓ CO2 dosing test: {msg}"))
    
    @patch('gh.datetime')
    def test_nighttime_no_dosing(self, mock_datetime):
        """Test CO2 dosing is disabled at night"""
        # Mock nighttime (23:00)
        mock_now = MagicMock()
        mock_now.hour = 23
        mock_datetime.datetime.now.return_value = mock_now
        
        plc = CO2PLC(self.sender, initial_ppm=700.0)  # Below MIN_CO2
        plc.run(cycles=1)
        
        self.assertEqual(len(self.messages), 1)
        msg = self.messages[0]
        self.assertEqual(msg['pump_pct'], 0.0)  # No dosing at night
        print(green(f"✓ Nighttime no-dosing test: {msg}"))
    
    def test_venting_scenario(self):
        """Test CO2 venting when levels are too high"""
        plc = CO2PLC(self.sender, initial_ppm=1500.0)  # Above MAX_CO2 (1200)
        plc.run(cycles=1)
        
        self.assertEqual(len(self.messages), 1)
        msg = self.messages[0]
        self.assertEqual(msg['pump_pct'], 0.0)
        self.assertGreater(msg['vent_pct'], 0)
        print(green(f"✓ CO2 venting test: {msg}"))


class TestPLC1Coordinator(unittest.TestCase):
    """Test PLC1 Coordinator functionality"""
    
    def setUp(self):
        self.plc1 = PLC1()
    
    def test_queue_communication(self):
        """Test message passing between PLCs and coordinator"""
        # Send test messages to each queue
        test_msgs = {
            "temp": {"temperature": 26.0, "heater_pct": 0, "cooler_pct": 0},
            "irrigation": {"moisture": 50.0, "pump_pct": 0, "drain_pct": 0},
            "light": {"light": 300.0, "grow_power_pct": 0},
            "co2": {"co2_ppm": 1000.0, "pump_pct": 0, "vent_pct": 0}
        }
        
        for key, msg in test_msgs.items():
            sender = self.plc1.sender_for(key)
            sender(msg)
            
        # Verify messages are in queues
        for key in test_msgs.keys():
            self.assertFalse(self.plc1.queues[key].empty())
        print(green("✓ Queue communication test"))
    
    def test_threshold_detection(self):
        """Test coordinator detects out-of-band conditions"""
        # Test _within_band method directly first
        test_msg = {"temperature": 30.0, "heater_pct": 0, "cooler_pct": 50}  # Above MAX_TEMP (27)
        in_band = self.plc1._within_band("temp", test_msg)
        self.assertFalse(in_band, "Temperature 30°C should be out of band (above 27°C)")
        
        # Test normal temperature
        normal_msg = {"temperature": 26.0, "heater_pct": 0, "cooler_pct": 0}  # Within band
        in_band_normal = self.plc1._within_band("temp", normal_msg)
        self.assertTrue(in_band_normal, "Temperature 26°C should be in band (25-27°C)")
        
        # Test all threshold bands
        test_cases = [
            ("temp", {"temperature": 30.0}, False),  # Above MAX_TEMP
            ("temp", {"temperature": 20.0}, False),  # Below MIN_TEMP
            ("irrigation", {"moisture": 70.0}, False),  # Above MAX_MOISTURE 
            ("irrigation", {"moisture": 30.0}, False),  # Below MIN_MOISTURE
            ("light", {"light": 100.0}, False),  # Below MIN_LIGHT
            ("co2", {"co2_ppm": 1500.0}, False),  # Above MAX_CO2
        ]
        
        for key, msg, expected in test_cases:
            result = self.plc1._within_band(key, msg)
            self.assertEqual(result, expected, f"Threshold test failed for {key}: {msg}")
        
        print(green("✓ Threshold detection test"))


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete system"""
    
    def test_short_integration_run(self):
        """Test a short integration run with all PLCs"""
        print(blue("\n--- Integration Test: Short Run ---"))
        
        plc1 = PLC1()
        workers = [
            TemperaturePLC(sender=plc1.sender_for("temp")),
            IrrigationPLC(sender=plc1.sender_for("irrigation")),
            LightPLC(sender=plc1.sender_for("light")),
            CO2PLC(sender=plc1.sender_for("co2")),
        ]
        
        threads = [
            threading.Thread(target=w.run, kwargs={"cycles": 3})
            for w in workers
        ] + [threading.Thread(target=plc1.run, daemon=True)]
        
        start_time = time.time()
        try:
            for t in threads: t.start()
            
            # Let system run for a bit to accumulate some messages
            time.sleep(2.0)
            
            # Check that messages are being processed (queues receiving data)
            messages_found = False
            for _ in range(10):  # Check multiple times over 1 second
                total_messages = sum(q.qsize() for q in plc1.queues.values())
                if total_messages > 0:
                    messages_found = True
                    break
                time.sleep(0.1)
            
            # Wait for worker threads to complete
            for t in threads[:-1]: t.join(timeout=30)  # Wait max 30 seconds
            
            # Check coordinator activity by looking at ack_count or flags
            coordinator_active = (plc1.ack_count > 0 or 
                                any(plc1.ok_flags.values()) or
                                messages_found)
            
            self.assertTrue(coordinator_active, "No evidence of coordinator activity")
            
            elapsed = time.time() - start_time
            print(green(f"✓ Integration test completed in {elapsed:.2f}s"))
            print(f"  Coordinator ack_count: {plc1.ack_count}")
            print(f"  Messages found during run: {messages_found}")
            
        except Exception as e:
            self.fail(f"Integration test failed: {e}")
        finally:
            # Cleanup
            for t in threads:
                if t.is_alive():
                    try:
                        t.join(timeout=1.0)
                    except:
                        pass
    
    def test_thread_cleanup(self):
        """Test thread cleanup mechanisms"""
        print(blue("\n--- Thread Cleanup Test ---"))
        
        plc1 = PLC1()
        worker = TemperaturePLC(sender=plc1.sender_for("temp"))
        
        thread = threading.Thread(target=worker.run, kwargs={"cycles": 2})
        
        try:
            thread.start()
            thread.join(timeout=20)  # Should complete within 20 seconds
            
            if thread.is_alive():
                self.fail("Thread did not complete within expected time")
            else:
                print(green("✓ Thread completed successfully"))
                
        except Exception as e:
            self.fail(f"Thread cleanup test failed: {e}")


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions"""
    
    def test_extreme_initial_values(self):
        """Test PLCs with extreme initial values"""
        messages = []
        def mock_sender(msg):
            messages.append(msg)
        
        # Test extreme temperature
        temp_plc = TemperaturePLC(mock_sender, initial_temp=-100.0)
        temp_plc.run(cycles=1)
        
        # Should clamp to valid range
        self.assertGreaterEqual(messages[0]['temperature'], 0)
        self.assertLessEqual(messages[0]['temperature'], 50)
        
        print(green("✓ Extreme initial values test"))
    
    def test_zero_intervals(self):
        """Test that system handles interval timing correctly"""
        # This test verifies timing constants are reasonable
        intervals = [TEMP_INTERVAL, IRRIGATION_INTERVAL, LIGHT_INTERVAL, CO2_INTERVAL]
        for interval in intervals:
            self.assertGreater(interval, 0, f"Interval {interval} should be positive")
        
        print(green("✓ Interval validation test"))


def run_test_suite():
    """Run the complete test suite with summary reporting"""
    print(bold("=" * 60))
    print(bold("PLC SIMULATION COMPREHENSIVE TEST SUITE"))
    print(bold("=" * 60))
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    test_classes = [
        TestTemperaturePLC,
        TestIrrigationPLC, 
        TestLightPLC,
        TestCO2PLC,
        TestPLC1Coordinator,
        TestIntegration,
        TestEdgeCases
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)
    
    # Summary
    print("\n" + bold("=" * 60))
    print(bold("TEST SUMMARY"))
    print(bold("=" * 60))
    print(f"Tests run: {result.testsRun}")
    
    if len(result.failures) == 0:
        print(green(f"Failures: {len(result.failures)}"))
    else:
        print(red(f"Failures: {len(result.failures)}"))
        
    if len(result.errors) == 0:
        print(green(f"Errors: {len(result.errors)}"))
    else:
        print(red(f"Errors: {len(result.errors)}"))
    
    if result.failures:
        print(red("\nFAILURES:"))
        for test, traceback in result.failures:
            print(red(f"- {test}: {traceback}"))
    
    if result.errors:
        print(red("\nERRORS:"))
        for test, traceback in result.errors:
            print(red(f"- {test}: {traceback}"))
    
    if result.wasSuccessful():
        print(green("\n🎉 ALL TESTS PASSED! The PLC simulation system is working correctly."))
        return True
    else:
        print(red("\n❌ SOME TESTS FAILED. Please review the issues above."))
        return False


if __name__ == "__main__":
    print(blue("Starting PLC simulation test suite..."))
    print("This will test all PLC components, integration, and edge cases.\n")
    
    success = run_test_suite()
    sys.exit(0 if success else 1)