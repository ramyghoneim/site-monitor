#!/usr/bin/env python3
"""
Site Monitor Bot - Track changes to websites in real-time.

Usage:
    python main.py                  # Run continuous monitoring
    python main.py --once           # Run single check
    python main.py --list           # List monitored sites
    python main.py --history <site> # Show history for a site
    python main.py --config <path>  # Use custom config file
    python main.py --init           # Create sample config file
"""

import argparse
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from site_monitor.bot import create_bot, SiteMonitorBot
from site_monitor.config import load_config, create_sample_config


def main():
    parser = argparse.ArgumentParser(
        description="Site Monitor Bot - Track changes to websites",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                    Start continuous monitoring
  python main.py --once             Run a single check
  python main.py --list             Show all monitored sites
  python main.py --history "Site"   Show change history for a site
  python main.py --config my.yaml   Use custom config file
  python main.py --init             Create sample config file
        """
    )

    parser.add_argument(
        '--config', '-c',
        default='config.yaml',
        help='Path to configuration file (default: config.yaml)'
    )
    parser.add_argument(
        '--once', '-1',
        action='store_true',
        help='Run a single check and exit'
    )
    parser.add_argument(
        '--list', '-l',
        action='store_true',
        help='List all monitored sites and their status'
    )
    parser.add_argument(
        '--history', '-H',
        metavar='SITE',
        help='Show change history for a specific site'
    )
    parser.add_argument(
        '--init',
        action='store_true',
        help='Create a sample configuration file'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    # Handle --init
    if args.init:
        if os.path.exists(args.config):
            print(f"Config file already exists: {args.config}")
            response = input("Overwrite? [y/N] ").strip().lower()
            if response != 'y':
                print("Aborted.")
                return
        create_sample_config(args.config)
        print(f"Sample configuration created: {args.config}")
        print("Edit this file to add your sites and run again.")
        return

    # Check config exists
    if not os.path.exists(args.config):
        print(f"Configuration file not found: {args.config}")
        print("Run with --init to create a sample configuration.")
        sys.exit(1)

    try:
        # Create bot
        bot = create_bot(args.config)

        # Override log level if verbose
        if args.verbose:
            import logging
            logging.getLogger().setLevel(logging.DEBUG)

        # Handle different modes
        if args.list:
            bot.list_sites()
        elif args.history:
            bot.show_history(args.history)
        elif args.once:
            bot.run_once()
        else:
            bot.run()

    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
