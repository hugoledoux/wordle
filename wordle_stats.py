#!/usr/bin/env python3
"""
Wordle Statistics Parser and Visualizer
Parses Telegram HTML export files to extract Wordle results and generate statistics
"""

import glob
import re
from collections import defaultdict
from datetime import datetime

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from bs4 import BeautifulSoup


def parse_html_files(pattern="history_dump/messages*.html", debug=False):
    """Parse all HTML files and extract Wordle results"""
    results = []

    for filename in sorted(glob.glob(pattern)):
        print(f"Processing {filename}...")
        with open(filename, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "html.parser")

            # Find all message divs
            messages = soup.find_all("div", class_="message")

            current_player = None
            for msg in messages:
                # Get the from_name
                from_name_div = msg.find("div", class_="from_name")
                if from_name_div:
                    current_player = from_name_div.get_text().strip()
                    current_player = re.sub(r"\s+via\s+@\w+", "", current_player)

                # Get the text content
                text_div = msg.find("div", class_="text")
                if not text_div:
                    continue

                text = text_div.get_text()

                # Check if it contains a Wordle result
                # Handle both formats: "Wordle 798 3/6" and "Wordle 1,292 3/6"
                wordle_match = re.search(r"Wordle ([\d,]+) ([X\d])/6", text)
                if wordle_match and current_player:
                    puzzle_num_str = wordle_match.group(1).replace(",", "")
                    puzzle_num = int(puzzle_num_str)
                    attempts = wordle_match.group(2)

                    # Get the date
                    date_div = msg.find("div", class_="details")
                    if date_div and date_div.get("title"):
                        date_str = date_div["title"]
                        # Parse date like "26.08.2023 08:38:51 UTC+01:00"
                        date_match = re.match(r"(\d{2})\.(\d{2})\.(\d{4})", date_str)
                        if date_match:
                            day, month, year = date_match.groups()
                            date = datetime(int(year), int(month), int(day))

                            results.append(
                                {
                                    "player": current_player,
                                    "puzzle_num": puzzle_num,
                                    "attempts": attempts,
                                    "date": date,
                                    "year": date.year,
                                }
                            )

    return results


def calculate_statistics(results):
    """Calculate statistics per player and year"""
    stats = defaultdict(
        lambda: defaultdict(
            lambda: {
                "total": 0,
                "wins": 0,
                "losses": 0,
                "attempts_dist": defaultdict(int),
                "total_attempts": 0,
            }
        )
    )

    for result in results:
        player = result["player"]
        year = result["year"]
        attempts = result["attempts"]

        stats[player][year]["total"] += 1

        if attempts == "X":
            stats[player][year]["losses"] += 1
        else:
            stats[player][year]["wins"] += 1
            attempts_num = int(attempts)
            stats[player][year]["attempts_dist"][attempts_num] += 1
            stats[player][year]["total_attempts"] += attempts_num

    return stats


def calculate_head_to_head(results):
    """Calculate head-to-head wins, losses, and ties per year"""
    # Group results by puzzle number and year
    puzzles = defaultdict(lambda: defaultdict(dict))

    for result in results:
        puzzle_num = result["puzzle_num"]
        year = result["year"]
        player = result["player"]
        attempts = result["attempts"]

        # Convert attempts to numeric value (X = 7 for comparison purposes)
        if attempts == "X":
            attempts_val = 7
        else:
            attempts_val = int(attempts)

        puzzles[year][puzzle_num][player] = attempts_val

    # Calculate wins/losses/ties per year
    h2h_stats = defaultdict(lambda: {"hugo_wins": 0, "sylvain_wins": 0, "ties": 0})

    for year, year_puzzles in puzzles.items():
        for puzzle_num, players in year_puzzles.items():
            if "Hugo Ledoux" in players and "Sylvain Roy" in players:
                hugo_attempts = players["Hugo Ledoux"]
                sylvain_attempts = players["Sylvain Roy"]

                if hugo_attempts < sylvain_attempts:
                    h2h_stats[year]["hugo_wins"] += 1
                elif sylvain_attempts < hugo_attempts:
                    h2h_stats[year]["sylvain_wins"] += 1
                else:
                    h2h_stats[year]["ties"] += 1

    return h2h_stats


def plot_statistics(stats, h2h_stats):
    """Create matplotlib visualizations"""
    players = sorted(stats.keys())

    # Get all years across all players
    all_years = sorted(
        set(year for player_stats in stats.values() for year in player_stats.keys())
    )

    # Create figure with multiple subplots (2x2 layout)
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle("Wordle: Battles of the titans", fontsize=16, fontweight="bold")

    # Flatten axes array for easier indexing
    axes = axes.flatten()

    # Define colors for players
    colors = {"Hugo Ledoux": "#3498db", "Sylvain Roy": "#e74c3c"}

    # 1. Total games per year
    ax1 = axes[0]
    x = range(len(all_years))
    width = 0.35

    for i, player in enumerate(players):
        totals = [
            stats[player][year]["total"] if year in stats[player] else 0
            for year in all_years
        ]
        offset = width * (i - 0.5)
        bars = ax1.bar(
            [xi + offset for xi in x],
            totals,
            width,
            label=player,
            color=colors.get(player, "#95a5a6"),
        )

        # Add value labels on bars
        for j, bar in enumerate(bars):
            height = bar.get_height()
            if height > 0:
                ax1.text(
                    bar.get_x() + bar.get_width() / 2.0,
                    height,
                    f"{int(height)}",
                    ha="center",
                    va="bottom",
                    fontsize=9,
                    fontweight="bold",
                )

    ax1.set_xlabel("Year", fontweight="bold")
    ax1.set_ylabel("Number of Games", fontweight="bold")
    ax1.set_title("Total Games Played per Year")
    ax1.set_xticks(x)
    ax1.set_xticklabels(all_years)
    ax1.legend()
    ax1.grid(axis="y", alpha=0.3)

    # 2. Average attempts per year (for wins only)
    ax2 = axes[1]
    for i, player in enumerate(players):
        avg_attempts = []
        for year in all_years:
            if year in stats[player] and stats[player][year]["wins"] > 0:
                avg = (
                    stats[player][year]["total_attempts"] / stats[player][year]["wins"]
                )
                avg_attempts.append(avg)
            else:
                avg_attempts.append(0)

        offset = width * (i - 0.5)
        bars = ax2.bar(
            [xi + offset for xi in x],
            avg_attempts,
            width,
            label=player,
            color=colors.get(player, "#95a5a6"),
        )

        # Add value labels on bars
        for j, bar in enumerate(bars):
            height = bar.get_height()
            if height > 0:
                ax2.text(
                    bar.get_x() + bar.get_width() / 2.0,
                    height,
                    f"{height:.2f}",
                    ha="center",
                    va="bottom",
                    fontsize=9,
                    fontweight="bold",
                )

    ax2.set_xlabel("Year", fontweight="bold")
    ax2.set_ylabel("Average Attempts", fontweight="bold")
    ax2.set_title("Average Attempts per Year (Wins Only)")
    ax2.set_xticks(x)
    ax2.set_xticklabels(all_years)
    ax2.legend()
    ax2.grid(axis="y", alpha=0.3)

    # 3. Attempts distribution (all years combined)
    ax3 = axes[2]
    attempts_range = range(1, 7)
    width_dist = 0.35
    x_dist = range(len(attempts_range) + 1)  # +1 for X/6

    for i, player in enumerate(players):
        dist = [0] * 7  # 1-6 plus X
        for year in all_years:
            if year in stats[player]:
                for attempt_num in attempts_range:
                    dist[attempt_num - 1] += stats[player][year]["attempts_dist"].get(
                        attempt_num, 0
                    )
                # Add losses (X/6) as the 7th bar
                dist[6] += stats[player][year]["losses"]

        offset = width_dist * (i - 0.5)
        bars = ax3.bar(
            [xi + offset for xi in x_dist],
            dist,
            width_dist,
            label=player,
            color=colors.get(player, "#95a5a6"),
        )

        # Add value labels on bars
        for j, bar in enumerate(bars):
            height = bar.get_height()
            if height > 0:
                ax3.text(
                    bar.get_x() + bar.get_width() / 2.0,
                    height,
                    f"{int(height)}",
                    ha="center",
                    va="bottom",
                    fontsize=9,
                    fontweight="bold",
                )

    ax3.set_xlabel("Number of Attempts", fontweight="bold")
    ax3.set_ylabel("Count", fontweight="bold")
    ax3.set_title("Distribution of Attempts (All Years)")
    ax3.set_xticks(x_dist)
    ax3.set_xticklabels([1, 2, 3, 4, 5, 6, "X"])
    ax3.legend()
    ax3.grid(axis="y", alpha=0.3)

    # 4. Head-to-head comparison per year (stacked bar chart)
    ax4 = axes[3]
    x_h2h = range(len(all_years))

    hugo_wins = [
        h2h_stats[year]["hugo_wins"] if year in h2h_stats else 0 for year in all_years
    ]
    sylvain_wins = [
        h2h_stats[year]["sylvain_wins"] if year in h2h_stats else 0
        for year in all_years
    ]
    ties = [h2h_stats[year]["ties"] if year in h2h_stats else 0 for year in all_years]

    # Create stacked bars (Hugo bottom, Sylvain middle, Ties top)
    ax4.bar(x_h2h, hugo_wins, label="Hugo Wins", color="#3498db")
    ax4.bar(
        x_h2h, sylvain_wins, bottom=hugo_wins, label="Sylvain Wins", color="#e74c3c"
    )

    # Stack ties on top
    bottom_ties = [h + s for h, s in zip(hugo_wins, sylvain_wins)]
    ax4.bar(x_h2h, ties, bottom=bottom_ties, label="Ties", color="#95a5a6")

    # Add percentage and count labels
    for i, year_idx in enumerate(x_h2h):
        total = hugo_wins[i] + ties[i] + sylvain_wins[i]
        if total > 0:
            # Hugo wins (bottom section)
            if hugo_wins[i] > 0:
                pct_hugo = hugo_wins[i] / total * 100
                y_pos_hugo = hugo_wins[i] / 2
                ax4.text(
                    year_idx,
                    y_pos_hugo,
                    f"{hugo_wins[i]}\n{pct_hugo:.1f}%",
                    ha="center",
                    va="center",
                    fontweight="bold",
                    fontsize=9,
                    color="white",
                )

            # Sylvain wins (middle section)
            if sylvain_wins[i] > 0:
                pct_sylvain = sylvain_wins[i] / total * 100
                y_pos_sylvain = hugo_wins[i] + sylvain_wins[i] / 2
                ax4.text(
                    year_idx,
                    y_pos_sylvain,
                    f"{sylvain_wins[i]}\n{pct_sylvain:.1f}%",
                    ha="center",
                    va="center",
                    fontweight="bold",
                    fontsize=9,
                    color="white",
                )

            # Ties (top section)
            if ties[i] > 0:
                pct_ties = ties[i] / total * 100
                y_pos_ties = hugo_wins[i] + sylvain_wins[i] + ties[i] / 2
                ax4.text(
                    year_idx,
                    y_pos_ties,
                    f"{ties[i]}\n{pct_ties:.1f}%",
                    ha="center",
                    va="center",
                    fontweight="bold",
                    fontsize=9,
                    color="white",
                )

    ax4.set_xlabel("Year", fontweight="bold")
    ax4.set_ylabel("Number of Games", fontweight="bold")
    ax4.set_title("Head-to-Head Daily Wins per Year")
    ax4.set_xticks(x_h2h)
    ax4.set_xticklabels(all_years)
    ax4.legend()
    ax4.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    plt.savefig("wordle_statistics.png", dpi=300, bbox_inches="tight")
    print("\nPlot saved as 'wordle_statistics.png'")
    plt.show()


def print_summary(stats):
    """Print summary statistics"""
    print("\n" + "=" * 80)
    print("WORDLE STATISTICS SUMMARY")
    print("=" * 80)

    for player in sorted(stats.keys()):
        print(f"\n{player}:")
        print("-" * 80)

        for year in sorted(stats[player].keys()):
            year_stats = stats[player][year]
            total = year_stats["total"]
            wins = year_stats["wins"]
            losses = year_stats["losses"]
            win_rate = (wins / total * 100) if total > 0 else 0
            avg_attempts = (year_stats["total_attempts"] / wins) if wins > 0 else 0

            print(f"  {year}:")
            print(f"    Total games: {total}")
            print(f"    Wins: {wins} ({win_rate:.1f}%)")
            print(f"    Losses: {losses}")
            print(f"    Average attempts (wins): {avg_attempts:.2f}")
            print("    Distribution: ", end="")
            for i in range(1, 7):
                count = year_stats["attempts_dist"].get(i, 0)
                if count > 0:
                    print(f"{i}:{count} ", end="")
            print()


if __name__ == "__main__":
    print("Parsing Telegram HTML files for Wordle results...")
    results = parse_html_files()
    print(f"\nFound {len(results)} Wordle results")

    print("\nCalculating statistics...")
    stats = calculate_statistics(results)

    print("\nCalculating head-to-head results...")
    h2h_stats = calculate_head_to_head(results)

    print_summary(stats)

    # Print head-to-head summary
    print("\n" + "=" * 80)
    print("HEAD-TO-HEAD COMPARISON (Daily Wins)")
    print("=" * 80)
    for year in sorted(h2h_stats.keys()):
        h2h = h2h_stats[year]
        total = h2h["hugo_wins"] + h2h["sylvain_wins"] + h2h["ties"]
        print(f"\n  {year}:")
        print(
            f"    Hugo wins: {h2h['hugo_wins']} ({h2h['hugo_wins'] / total * 100:.1f}%)"
        )
        print(
            f"    Sylvain wins: {h2h['sylvain_wins']} ({h2h['sylvain_wins'] / total * 100:.1f}%)"
        )
        print(f"    Ties: {h2h['ties']} ({h2h['ties'] / total * 100:.1f}%)")
        print(f"    Total head-to-head games: {total}")

    print("\nGenerating visualizations...")
    plot_statistics(stats, h2h_stats)
    print("\nDone!")
