"""
MT4 Strategy Tester - Command Line Interface
Automated Python script for MT4 strategy testing via command line using configuration files
"""

import subprocess
import argparse
import os
import sys
import time
import glob
import re
from datetime import datetime, timedelta
from pathlib import Path
from html.parser import HTMLParser

class MT4ReportParser(HTMLParser):
    """Parse MT4 HTML report files to extract test results"""
    
    def __init__(self):
        super().__init__()
        self.in_table = False
        self.current_row = []
        self.data = {}
        self.trades = []
        self.current_tag = None
        
    def handle_starttag(self, tag, attrs):
        if tag == 'table':
            self.in_table = True
        elif tag == 'tr':
            self.current_row = []
        self.current_tag = tag
    
    def handle_data(self, data):
        data = data.strip()
        if data and self.in_table:
            self.current_row.append(data)
    
    def handle_endtag(self, tag):
        if tag == 'table':
            self.in_table = False
        elif tag == 'tr' and self.current_row:
            # Parse key-value pairs
            if len(self.current_row) >= 2:
                key = self.current_row[0]
                value = self.current_row[1] if len(self.current_row) > 1 else ""
                self.data[key] = value


class MT4ReportGenerator:
    """Generate comprehensive reports from MT4 test results"""
    
    def __init__(self, data_folder=None):
        self.data_folder = data_folder
    
    def find_mt4_reports(self, ea_name="RandomTrader", max_age_hours=2):
        """
        Find recent MT4 report files
        
        Args:
            ea_name: Expert Advisor name
            max_age_hours: Maximum age of report files to consider (hours)
            
        Returns:
            List of report file paths sorted by modification time (newest first)
        """
        report_files = []
        
        # Common MT4 report locations
        appdata = os.getenv('APPDATA')
        possible_locations = []
        
        if appdata:
            terminal_base = os.path.join(appdata, 'MetaQuotes', 'Terminal')
            if os.path.exists(terminal_base):
                for item in os.listdir(terminal_base):
                    tester_reports = os.path.join(terminal_base, item, 'tester', 'reports')
                    if os.path.exists(tester_reports):
                        possible_locations.append(tester_reports)
        
        # Search for report files
        cutoff_time = time.time() - (max_age_hours * 3600)
        
        for location in possible_locations:
            pattern = os.path.join(location, f"{ea_name}*.htm")
            files = glob.glob(pattern)
            
            for file in files:
                # Check file modification time
                if os.path.getmtime(file) >= cutoff_time:
                    report_files.append(file)
        
        # Sort by modification time (newest first)
        report_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        
        return report_files
    
    def parse_html_report(self, report_file):
        """
        Parse MT4 HTML report file
        
        Args:
            report_file: Path to HTML report file
            
        Returns:
            Dictionary with parsed report data
        """
        try:
            with open(report_file, 'r', encoding='utf-8', errors='ignore') as f:
                html_content = f.read()
            
            parser = MT4ReportParser()
            parser.feed(html_content)
            
            return parser.data
        except Exception as e:
            print(f"Error parsing report: {e}")
            return {}
    
    def extract_report_summary(self, report_data):
        """
        Extract key metrics from report data
        
        Args:
            report_data: Dictionary with parsed report data
            
        Returns:
            Dictionary with summary metrics
        """
        summary = {
            'total_net_profit': self._extract_value(report_data, 'Total net profit'),
            'gross_profit': self._extract_value(report_data, 'Gross profit'),
            'gross_loss': self._extract_value(report_data, 'Gross loss'),
            'profit_factor': self._extract_value(report_data, 'Profit factor'),
            'expected_payoff': self._extract_value(report_data, 'Expected payoff'),
            'absolute_drawdown': self._extract_value(report_data, 'Absolute drawdown'),
            'maximal_drawdown': self._extract_value(report_data, 'Maximal drawdown'),
            'relative_drawdown': self._extract_value(report_data, 'Relative drawdown'),
            'total_trades': self._extract_value(report_data, 'Total trades'),
            'short_positions': self._extract_value(report_data, 'Short positions (won %)'),
            'long_positions': self._extract_value(report_data, 'Long positions (won %)'),
            'profit_trades': self._extract_value(report_data, 'Profit trades (% of total)'),
            'loss_trades': self._extract_value(report_data, 'Loss trades (% of total)'),
            'largest_profit': self._extract_value(report_data, 'Largest profit trade'),
            'largest_loss': self._extract_value(report_data, 'Largest loss trade'),
            'average_profit': self._extract_value(report_data, 'Average profit trade'),
            'average_loss': self._extract_value(report_data, 'Average loss trade'),
            'maximum_consecutive_wins': self._extract_value(report_data, 'Maximum consecutive wins'),
            'maximum_consecutive_losses': self._extract_value(report_data, 'Maximum consecutive losses'),
            'initial_deposit': self._extract_value(report_data, 'Initial deposit'),
            'total_balance': self._extract_value(report_data, 'Balance'),
        }
        
        return summary
    
    def _extract_value(self, data, key):
        """Extract numeric value from report data"""
        value = data.get(key, '')
        if not value:
            return 'N/A'
        
        # Try to extract first numeric value
        numbers = re.findall(r'-?\d+\.?\d*', str(value))
        if numbers:
            try:
                return float(numbers[0])
            except ValueError:
                pass
        
        return value
    
    def generate_text_report(self, report_file, config_details=None):
        """
        Generate a text-based summary report from MT4 HTML report
        
        Args:
            report_file: Path to MT4 HTML report file
            config_details: Dictionary with test configuration
            
        Returns:
            String with formatted report
        """
        print(f"\n📊 Parsing MT4 report: {report_file}")
        
        report_data = self.parse_html_report(report_file)
        summary = self.extract_report_summary(report_data)
        
        # Build report
        report_lines = []
        report_lines.append("=" * 70)
        report_lines.append("MT4 STRATEGY TEST REPORT")
        report_lines.append("=" * 70)
        report_lines.append(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"Source: {os.path.basename(report_file)}")
        
        if config_details:
            report_lines.append(f"\n{'─' * 70}")
            report_lines.append("TEST CONFIGURATION")
            report_lines.append(f"{'─' * 70}")
            report_lines.append(f"Expert Advisor:      {config_details.get('ea_name', 'N/A')}")
            report_lines.append(f"Symbol:              {config_details.get('symbol', 'N/A')}")
            report_lines.append(f"Timeframe:           M{config_details.get('timeframe', 'N/A')}")
            report_lines.append(f"Test Period:         {config_details.get('start_date', 'N/A')} to {config_details.get('end_date', 'N/A')}")
            report_lines.append(f"Lot Size:            {config_details.get('lot_size', 'N/A')}")
            report_lines.append(f"Candle Interval:     {config_details.get('candle_interval', 'N/A')}")
        
        report_lines.append(f"\n{'─' * 70}")
        report_lines.append("PERFORMANCE SUMMARY")
        report_lines.append(f"{'─' * 70}")
        report_lines.append(f"Initial Deposit:     ${summary['initial_deposit']}")
        report_lines.append(f"Final Balance:       ${summary['total_balance']}")
        report_lines.append(f"Total Net Profit:    ${summary['total_net_profit']}")
        report_lines.append(f"Gross Profit:        ${summary['gross_profit']}")
        report_lines.append(f"Gross Loss:          ${summary['gross_loss']}")
        report_lines.append(f"Profit Factor:       {summary['profit_factor']}")
        report_lines.append(f"Expected Payoff:     ${summary['expected_payoff']}")
        
        report_lines.append(f"\n{'─' * 70}")
        report_lines.append("DRAWDOWN ANALYSIS")
        report_lines.append(f"{'─' * 70}")
        report_lines.append(f"Absolute Drawdown:   ${summary['absolute_drawdown']}")
        report_lines.append(f"Maximal Drawdown:    {summary['maximal_drawdown']}")
        report_lines.append(f"Relative Drawdown:   {summary['relative_drawdown']}")
        
        report_lines.append(f"\n{'─' * 70}")
        report_lines.append("TRADING STATISTICS")
        report_lines.append(f"{'─' * 70}")
        report_lines.append(f"Total Trades:        {summary['total_trades']}")
        report_lines.append(f"Long Positions:      {summary['long_positions']}")
        report_lines.append(f"Short Positions:     {summary['short_positions']}")
        report_lines.append(f"Profit Trades:       {summary['profit_trades']}")
        report_lines.append(f"Loss Trades:         {summary['loss_trades']}")
        
        report_lines.append(f"\n{'─' * 70}")
        report_lines.append("TRADE ANALYSIS")
        report_lines.append(f"{'─' * 70}")
        report_lines.append(f"Largest Profit:      ${summary['largest_profit']}")
        report_lines.append(f"Largest Loss:        ${summary['largest_loss']}")
        report_lines.append(f"Average Profit:      ${summary['average_profit']}")
        report_lines.append(f"Average Loss:        ${summary['average_loss']}")
        report_lines.append(f"Max Consecutive Wins:   {summary['maximum_consecutive_wins']}")
        report_lines.append(f"Max Consecutive Losses: {summary['maximum_consecutive_losses']}")
        
        report_lines.append(f"\n{'─' * 70}")
        report_lines.append("REPORT FILES")
        report_lines.append(f"{'─' * 70}")
        report_lines.append(f"HTML Report:         {report_file}")
        
        report_lines.append("\n" + "=" * 70)
        
        return "\n".join(report_lines)
    
    def save_report(self, report_text, output_file=None):
        """
        Save report to file
        
        Args:
            report_text: Report text content
            output_file: Output file path (default: auto-generate)
            
        Returns:
            Path to saved report file
        """
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"mt4_test_report_{timestamp}.txt"
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report_text)
            print(f"✓ Report saved: {output_file}")
            return output_file
        except Exception as e:
            print(f"Error saving report: {e}")
            return None
    
    def wait_for_report(self, ea_name="RandomTrader", timeout=15, check_interval=5):
        """
        Wait for MT4 test to complete and report to be generated
        
        Args:
            ea_name: Expert Advisor name
            timeout: Maximum wait time in seconds
            check_interval: Time between checks in seconds
            
        Returns:
            Path to report file or None if timeout
        """
        print(f"\n⏳ Waiting for MT4 test to complete (timeout: {timeout}s)...")
        
        start_time = time.time()
        last_file_count = 0
        
        while (time.time() - start_time) < timeout:
            reports = self.find_mt4_reports(ea_name, max_age_hours=1)
            
            if reports:
                current_count = len(reports)
                if current_count > last_file_count:
                    # New report detected
                    print(f"✓ Report file detected: {reports[0]}")
                    # Wait a bit more to ensure file is fully written
                    time.sleep(2)
                    return reports[0]
                last_file_count = current_count
            
            elapsed = int(time.time() - start_time)
            print(f"  Waiting... ({elapsed}/{timeout}s)", end='\r')
            time.sleep(check_interval)
        
        print(f"\n⚠ Timeout reached. No new report found.")
        return None

class MT4StrategyTester:
    def __init__(self, mt4_path, mt4_data_folder=None):
        """
        Initialize MT4 Strategy Tester
        
        Args:
            mt4_path: Path to MT4 terminal.exe
            mt4_data_folder: Path to MT4 data folder (optional, will auto-detect)
        """
        self.mt4_path = mt4_path
        
        if not os.path.exists(mt4_path):
            raise FileNotFoundError(f"MT4 terminal not found at: {mt4_path}")
        
        # Get MT4 installation directory
        self.mt4_dir = os.path.dirname(mt4_path)
        
        # Auto-detect MT4 data folder if not provided
        if mt4_data_folder:
            self.data_folder = mt4_data_folder
        else:
            # Common MT4 data folder locations
            # Try standard AppData location first
            appdata = os.getenv('APPDATA')
            possible_paths = [
                os.path.join(appdata, 'MetaQuotes', 'Terminal') if appdata else None,
                os.path.join(self.mt4_dir, 'MQL4'),
                os.path.join(os.path.dirname(self.mt4_dir), 'MQL4')
            ]
            
            self.data_folder = None
            for path in possible_paths:
                if path and os.path.exists(path):
                    self.data_folder = path
                    break
            
            if not self.data_folder:
                self.data_folder = os.path.join(self.mt4_dir, 'MQL4')
                print(f"Warning: Could not find MT4 data folder, using: {self.data_folder}")
            
        print(f"MT4 Terminal: {self.mt4_path}")
        print(f"MT4 Data Folder: {self.data_folder}")
    
    def create_ea_preset(self, test_date, lot_size, candle_interval, output_file=None):
        """
        Create EA parameter preset file (.set) for MT4
        
        Args:
            test_date: Test date as string "YYYY-MM-DD"
            lot_size: Trade lot size
            candle_interval: Number of candles between trades
            output_file: Output preset file name (default: RandomTrader.set)
        """
        if output_file is None:
            output_file = "RandomTrader.set"
        
        # MT4 .set file format
        preset_content = f""";
; EA Parameters Preset
; Generated by mt4_tester.py
;
TestDate={test_date}
||
{test_date}
CandleInterval={candle_interval}
||
{candle_interval}
LotSize={lot_size:.2f}
||
{lot_size:.2f}
MagicNumber=123456
||
123456
"""
        
        try:
            with open(output_file, 'w') as f:
                f.write(preset_content)
            print(f"EA preset file created: {output_file}")
            return output_file
        except Exception as e:
            print(f"Error creating preset file: {e}")
            return None
    
    def generate_mt4_config(self, symbol, timeframe, test_date, ea_name, 
                           lot_size=0.01, candle_interval=5, 
                           output_file="mt4_test_config.ini",
                           shutdown=False, visual=False):
        """
        Generate MT4 configuration file for automated testing
        
        Args:
            symbol: Trading symbol (e.g., "US100.f")
            timeframe: Chart timeframe (M1, M5, M15, M30, H1, H4, D1, W1, MN)
            test_date: Test date as string "YYYY-MM-DD"
            ea_name: Name of the Expert Advisor
            lot_size: Trade lot size
            candle_interval: Number of candles between trades
            output_file: Output configuration file name
            shutdown: Shutdown terminal after test completion
            visual: Enable visual testing mode
        """
        # Calculate date range (3 days before test_date)
        try:
            end_date = datetime.strptime(test_date, "%Y-%m-%d")
            start_date = end_date - timedelta(days=3)
        except ValueError:
            print(f"Invalid date format: {test_date}. Use YYYY-MM-DD")
            return None
        
        # Convert timeframe number to MT4 format
        timeframe_map = {
            1: 'M1', 5: 'M5', 15: 'M15', 30: 'M30',
            60: 'H1', 240: 'H4', 1440: 'D1', 10080: 'W1', 43200: 'MN'
        }
        
        if isinstance(timeframe, int):
            tf_str = timeframe_map.get(timeframe, 'M15')
        else:
            tf_str = timeframe
        
        # Create preset file for EA parameters
        preset_file = self.create_ea_preset(test_date, lot_size, candle_interval)
        
        # Generate report filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_name = f"{ea_name}_Report_{timestamp}"
        
        # MT4 configuration file content
        config = f"""; MT4 Strategy Tester Configuration
; Generated by mt4_tester.py on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

; Enable Experts
ExpertsEnable=true
ExpertsDllImport=false
ExpertsExpImport=false
ExpertsTrades=true

; Strategy Tester Settings
TestExpert={ea_name}
TestExpertParameters={os.path.basename(preset_file) if preset_file else ''}
TestSymbol={symbol}
TestPeriod={tf_str}
TestModel=0
TestSpread=0
TestOptimization=false
TestDateEnable=true
TestFromDate={start_date.strftime('%Y.%m.%d')}
TestToDate={end_date.strftime('%Y.%m.%d')}
TestReport={report_name}
TestReplaceReport=true
TestShutdownTerminal={'true' if shutdown else 'false'}
TestVisualEnable={'true' if visual else 'false'}
"""
        
        try:
            with open(output_file, 'w') as f:
                f.write(config.strip())
            print(f"\n{'='*60}")
            print(f"Configuration file created: {output_file}")
            print(f"{'='*60}")
            print(f"Symbol: {symbol}")
            print(f"Timeframe: {tf_str}")
            print(f"Test Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
            print(f"EA: {ea_name}")
            print(f"Lot Size: {lot_size}")
            print(f"Candle Interval: {candle_interval}")
            print(f"Report: {report_name}.htm")
            print(f"Visual Mode: {'Enabled' if visual else 'Disabled'}")
            print(f"Auto-shutdown: {'Enabled' if shutdown else 'Disabled'}")
            return output_file
        except Exception as e:
            print(f"Error creating config file: {e}")
            return None
    
    def copy_ea_to_mt4(self, ea_file):
        """
        Copy Expert Advisor to MT4 Experts folder
        
        Args:
            ea_file: Path to the .mq4 or .ex4 file
        """
        if not os.path.exists(ea_file):
            print(f"Warning: EA file not found: {ea_file}")
            return None
        
        # Try to find Experts folder
        possible_experts_folders = [
            os.path.join(self.data_folder, "Experts"),
            os.path.join(self.mt4_dir, "MQL4", "Experts"),
        ]
        
        # Check AppData locations
        appdata = os.getenv('APPDATA')
        if appdata:
            # Search for Terminal folders
            terminal_base = os.path.join(appdata, 'MetaQuotes', 'Terminal')
            if os.path.exists(terminal_base):
                for item in os.listdir(terminal_base):
                    possible_path = os.path.join(terminal_base, item, 'MQL4', 'Experts')
                    if os.path.exists(possible_path):
                        possible_experts_folders.append(possible_path)
        
        experts_folder = None
        for folder in possible_experts_folders:
            if os.path.exists(folder):
                experts_folder = folder
                break
        
        if not experts_folder:
            print(f"Warning: Could not find MT4 Experts folder automatically")
            print(f"Please manually copy {ea_file} to your MT4 Experts folder")
            return None
        
        ea_filename = os.path.basename(ea_file)
        dest_path = os.path.join(experts_folder, ea_filename)
        
        try:
            import shutil
            shutil.copy2(ea_file, dest_path)
            print(f"✓ EA copied to: {dest_path}")
            return dest_path
        except Exception as e:
            print(f"Error copying EA: {e}")
            return None
    
    def copy_preset_to_tester(self, preset_file):
        """
        Copy preset file to MT4 tester directory
        
        Args:
            preset_file: Path to the .set file
        """
        if not os.path.exists(preset_file):
            print(f"Warning: Preset file not found: {preset_file}")
            return None
        
        # Try to find tester folder
        possible_tester_folders = [
            os.path.join(self.data_folder, "..", "tester"),
            os.path.join(self.mt4_dir, "tester"),
        ]
        
        # Check AppData locations
        appdata = os.getenv('APPDATA')
        if appdata:
            terminal_base = os.path.join(appdata, 'MetaQuotes', 'Terminal')
            if os.path.exists(terminal_base):
                for item in os.listdir(terminal_base):
                    possible_path = os.path.join(terminal_base, item, 'tester')
                    if os.path.exists(possible_path):
                        possible_tester_folders.append(possible_path)
        
        tester_folder = None
        for folder in possible_tester_folders:
            if os.path.exists(folder):
                tester_folder = folder
                break
        
        if not tester_folder:
            print(f"Warning: Could not find MT4 tester folder automatically")
            return None
        
        preset_filename = os.path.basename(preset_file)
        dest_path = os.path.join(tester_folder, preset_filename)
        
        try:
            import shutil
            shutil.copy2(preset_file, dest_path)
            print(f"✓ Preset copied to: {dest_path}")
            return dest_path
        except Exception as e:
            print(f"Error copying preset: {e}")
            return None
    
    def compile_ea(self, ea_file):
        """
        Compile MQL4 Expert Advisor
        Note: Requires MetaEditor or MT4 to be running
        
        Args:
            ea_file: Path to .mq4 file
        """
        print(f"\nTo compile the EA ({os.path.basename(ea_file)}):")
        print("1. Open MT4 MetaEditor (F4 from MT4)")
        print(f"2. Open the file: {ea_file}")
        print("3. Press F7 or click Compile button")
        print("Or: Place the .mq4 file in MT4's Experts folder and restart MT4 to auto-compile")
    
    def launch_mt4_with_config(self, config_file):
        """
        Launch MT4 terminal with configuration file for automated testing
        
        Args:
            config_file: Path to the .ini configuration file
        """
        if not os.path.exists(config_file):
            print(f"Error: Configuration file not found: {config_file}")
            return False
        
        # Get absolute path to config file
        config_path = os.path.abspath(config_file)
        
        try:
            print(f"\n{'='*60}")
            print(f"Launching MT4 with automated testing...")
            print(f"Config: {config_path}")
            print(f"{'='*60}\n")
            
            # Launch MT4 with config file
            cmd = [self.mt4_path, config_path]
            process = subprocess.Popen(cmd)
            
            print("✓ MT4 launched successfully with test configuration!")
            print("\nMT4 will automatically:")
            print("  1. Load the RandomTrader EA")
            print("  2. Configure the Strategy Tester")
            print("  3. Start the backtest")
            print("  4. Generate a report when complete")
            print("\nYou can watch the progress in MT4's Strategy Tester window.")
            
            # Return the config path for summary
            return config_path
        except Exception as e:
            print(f"Error launching MT4: {e}")
            return False
    
    def run_test(self, symbol="US100.f", timeframe=15, test_date=None, 
                 ea_name="RandomTrader", lot_size=0.01, candle_interval=5,
                 shutdown=False, visual=False, auto_launch=True):
        """
        Run MT4 strategy test with full automation
        
        Args:
            symbol: Trading symbol
            timeframe: Chart timeframe in minutes
            test_date: Test date (defaults to 3 days ago)
            ea_name: Expert Advisor name
            lot_size: Trade lot size
            candle_interval: Number of candles between trades
            shutdown: Shutdown MT4 after test completion
            visual: Enable visual testing mode
            auto_launch: Automatically launch MT4 with config
            
        Returns:
            dict with test configuration details or None on failure
        """
        if test_date is None:
            test_date = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
        
        print(f"\n{'='*60}")
        print(f"MT4 AUTOMATED STRATEGY TESTER")
        print(f"{'='*60}")
        
        # Check if EA file exists
        ea_file = os.path.join(os.getcwd(), f"{ea_name}.mq4")
        if os.path.exists(ea_file):
            print(f"\n✓ Found EA file: {ea_file}")
            # Try to copy EA to MT4
            self.copy_ea_to_mt4(ea_file)
        else:
            print(f"\n⚠ EA file not found in current directory: {ea_file}")
            print(f"  Make sure {ea_name}.mq4 is copied to MT4's Experts folder")
        
        # Calculate date range for display
        try:
            end_date = datetime.strptime(test_date, "%Y-%m-%d")
            start_date = end_date - timedelta(days=3)
        except ValueError:
            print(f"Invalid date format: {test_date}")
            return None
        
        # Generate configuration
        config_file = self.generate_mt4_config(
            symbol=symbol,
            timeframe=timeframe,
            test_date=test_date,
            ea_name=ea_name,
            lot_size=lot_size,
            candle_interval=candle_interval,
            shutdown=shutdown,
            visual=visual
        )
        
        if not config_file:
            return None
        
        # Copy preset file to tester folder
        preset_file = f"{ea_name}.set"
        if os.path.exists(preset_file):
            self.copy_preset_to_tester(preset_file)
        
        print(f"\n{'='*60}")
        print("SETUP COMPLETE")
        print(f"{'='*60}")
        
        # Store configuration details for summary
        config_details = {
            'symbol': symbol,
            'timeframe': timeframe,
            'test_date': test_date,
            'start_date': start_date.strftime("%Y-%m-%d"),
            'end_date': end_date.strftime("%Y-%m-%d"),
            'ea_name': ea_name,
            'lot_size': lot_size,
            'candle_interval': candle_interval,
            'visual': visual,
            'shutdown': shutdown,
            'config_file': config_file
        }
        
        if auto_launch:
            launch_result = self.launch_mt4_with_config(config_file)
            config_details['launched'] = launch_result is not None
            return config_details
        else:
            print(f"\nTo start testing, run:")
            print(f'  "{self.mt4_path}" "{os.path.abspath(config_file)}"')
            config_details['launched'] = False
            return config_details
    
    def launch_mt4(self):
        """
        Launch MT4 terminal without configuration
        """
        try:
            print(f"\nLaunching MT4 from: {self.mt4_path}")
            subprocess.Popen([self.mt4_path])
            print("✓ MT4 launched successfully!")
            return True
        except Exception as e:
            print(f"Error launching MT4: {e}")
            return False


def print_summary(config_details):
    """
    Print a comprehensive summary of the test configuration
    
    Args:
        config_details: Dictionary with test configuration
    """
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    
    print(f"\n📊 Test Configuration:")
    print(f"  Expert Advisor:    {config_details['ea_name']}")
    print(f"  Symbol:            {config_details['symbol']}")
    print(f"  Timeframe:         M{config_details['timeframe']}")
    print(f"  Test Date:         {config_details['test_date']}")
    print(f"  Date Range:        {config_details['start_date']} to {config_details['end_date']}")
    print(f"  Duration:          3 days")
    
    print(f"\n⚙️  Trading Parameters:")
    print(f"  Lot Size:          {config_details['lot_size']}")
    print(f"  Trade Interval:    Every {config_details['candle_interval']} M{config_details['timeframe']} candles")
    print(f"  Trade Logic:       Random BUY or SELL")
    
    print(f"\n🎮 Testing Options:")
    print(f"  Visual Mode:       {'✓ Enabled' if config_details['visual'] else '✗ Disabled'}")
    print(f"  Auto-Shutdown:     {'✓ Enabled' if config_details['shutdown'] else '✗ Disabled'}")
    
    print(f"\n📁 Generated Files:")
    print(f"  Config File:       {config_details['config_file']}")
    print(f"  Preset File:       {config_details['ea_name']}.set")
    
    if config_details.get('launched'):
        print(f"\n🚀 Status:")
        print(f"  ✓ MT4 launched successfully!")
        print(f"  ✓ Test is running automatically")
        
        print(f"\n📈 What's Happening Now:")
        print(f"  1. MT4 Strategy Tester is loading historical data")
        print(f"  2. RandomTrader EA will execute random trades")
        print(f"  3. Results will be compiled into an HTML report")
        
        if config_details['visual']:
            print(f"\n👁️  Visual Mode:")
            print(f"  - Watch the chart in real-time")
            print(f"  - See each trade as it executes")
            print(f"  - Monitor equity curve changes")
        
        if config_details['shutdown']:
            print(f"\n⏹️  Auto-Shutdown:")
            print(f"  - MT4 will close automatically when test completes")
            print(f"  - Check for the report file in MT4 directory")
        else:
            print(f"\n📊 After Completion:")
            print(f"  - Open Strategy Tester in MT4 (Ctrl+R)")
            print(f"  - View Results, Graph, and Report tabs")
            print(f"  - Check for HTML report file")
    else:
        print(f"\n⚠️  Status:")
        print(f"  MT4 not launched automatically")
        print(f"  Run the command shown above to start testing")
    
    print(f"\n💡 Expected Results:")
    expected_candles = 3 * 24 * 4  # 3 days * 24 hours * 4 M15 candles per hour
    expected_trades = expected_candles // config_details['candle_interval']
    print(f"  Expected Candles:  ~{expected_candles} M15 candles")
    print(f"  Expected Trades:   ~{expected_trades} trades")
    print(f"  Trade Volume:      {expected_trades * config_details['lot_size']:.2f} lots total")
    
    print(f"\n{'='*60}")


def main():
    """
    Main function to run MT4 strategy tester from command line
    """
    parser = argparse.ArgumentParser(
        description="MT4 Strategy Tester - Automated Command Line Interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fully automated test with today's date (auto-launch MT4)
  python mt4_tester.py
  
  # Test with specific date (fully automated)
  python mt4_tester.py --date 2025-11-09
  
  # Test with custom parameters and visual mode
  python mt4_tester.py --date 2025-11-09 --visual --lot 0.02
  
  # Test with auto-shutdown and wait for report
  python mt4_tester.py --date 2025-11-09 --shutdown --wait
  
  # Test and wait for report (with custom timeout)
  python mt4_tester.py --date 2025-11-09 --wait --report-timeout 600
  
  # Generate report from most recent test
  python mt4_tester.py --generate-report
  
  # Generate config but don't launch MT4
  python mt4_tester.py --date 2025-11-09 --no-launch
  
  # Launch MT4 only (no testing)
  python mt4_tester.py --launch-only
  
  # Full example with all options
  python mt4_tester.py --symbol US100.f --timeframe 15 --date 2025-11-09 \\
      --lot 0.01 --interval 5 --visual --shutdown --wait
        """
    )
    
    parser.add_argument(
        '--mt4-path',
        default=r'C:\Program Files (x86)\mForex Trader\terminal.exe',
        help='Path to MT4 terminal.exe'
    )
    
    parser.add_argument(
        '--symbol',
        default='US100.f',
        help='Trading symbol (default: US100.f)'
    )
    
    parser.add_argument(
        '--timeframe',
        type=int,
        default=15,
        help='Chart timeframe in minutes (default: 15 for M15)'
    )
    
    parser.add_argument(
        '--date',
        help='Test date in YYYY-MM-DD format (default: 3 days ago)'
    )
    
    parser.add_argument(
        '--lot',
        type=float,
        default=0.01,
        help='Lot size (default: 0.01)'
    )
    
    parser.add_argument(
        '--interval',
        type=int,
        default=5,
        help='Number of M15 candles between trades (default: 5)'
    )
    
    parser.add_argument(
        '--ea-name',
        default='RandomTrader',
        help='Expert Advisor name (default: RandomTrader)'
    )
    
    parser.add_argument(
        '--shutdown',
        action='store_true',
        help='Shutdown MT4 after test completion'
    )
    
    parser.add_argument(
        '--visual',
        action='store_true',
        help='Enable visual testing mode'
    )
    
    parser.add_argument(
        '--no-launch',
        action='store_true',
        help='Generate config but do not launch MT4'
    )
    
    parser.add_argument(
        '--launch-only',
        action='store_true',
        help='Only launch MT4, skip test configuration'
    )
    
    parser.add_argument(
        '--wait',
        action='store_true',
        help='Wait for test to complete and generate report'
    )
    
    parser.add_argument(
        '--generate-report',
        action='store_true',
        help='Generate report from most recent MT4 test (without waiting)'
    )
    
    parser.add_argument(
        '--report-timeout',
        type=int,
        default=15,
        help='Timeout in seconds when waiting for report (default: 15)'
    )
    
    args = parser.parse_args()
    
    try:
        tester = MT4StrategyTester(args.mt4_path)
        report_gen = MT4ReportGenerator()
        
        if args.launch_only:
            tester.launch_mt4()
        elif args.generate_report:
            # Generate report from most recent test
            print("\n🔍 Searching for recent MT4 reports...")
            reports = report_gen.find_mt4_reports(args.ea_name, max_age_hours=24)
            
            if reports:
                print(f"✓ Found {len(reports)} recent report(s)")
                report_file = reports[0]
                
                # Generate and display report
                report_text = report_gen.generate_text_report(report_file)
                print("\n" + report_text)
                
                # Save report
                output_file = report_gen.save_report(report_text)
                
                print(f"\n✓ Report generation complete!")
            else:
                print("❌ No recent MT4 reports found")
                print("   Make sure a test has been run recently")
                sys.exit(1)
        else:
            # Run the automated test
            config_details = tester.run_test(
                symbol=args.symbol,
                timeframe=args.timeframe,
                test_date=args.date,
                ea_name=args.ea_name,
                lot_size=args.lot,
                candle_interval=args.interval,
                shutdown=args.shutdown,
                visual=args.visual,
                auto_launch=not args.no_launch
            )
            
            if config_details:
                # Print comprehensive summary
                print_summary(config_details)
                
                # Wait for report if requested
                if args.wait and config_details.get('launched'):
                    report_file = report_gen.wait_for_report(
                        args.ea_name, 
                        timeout=args.report_timeout
                    )
                    
                    if report_file:
                        # Generate and display report
                        report_text = report_gen.generate_text_report(
                            report_file, 
                            config_details
                        )
                        print("\n" + report_text)
                        
                        # Save report
                        output_file = report_gen.save_report(report_text)
                        
                        print(f"\n✓ Test complete! Report saved to: {output_file}")
                    else:
                        print("\n⚠ Could not find report file")
                        print("   The test may still be running or may have failed")
                        print("   Use --generate-report to try again later")
            else:
                print("\n❌ Test setup failed!")
                sys.exit(1)
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
