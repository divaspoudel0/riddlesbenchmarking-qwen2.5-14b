from __future__ import annotations
from resources_used import *
from local_specificity import *
from time_per_riddle import *
from topic_difficulty import *
from within_community_confidence import *
from confidence_distribution import *
from cross_community_within_language import *
from top_15_codes import *
from AI_usage_breakdown import *


def main():
    calculate_used_resources()
    calculate_local_specificity()
    calculate_topic_difficulty()
    within_confidence()
    time_per_riddle()
    confidence_distribution()
    arabic_difficuty()
    indonesian_difficulty()
    bengali_difficulty()
    portuguese_difficulty()
    ai_usage_breakdown()
    top_codes()


if __name__== "__main__":
    main()