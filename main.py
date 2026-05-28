# main.py
# CHANGED: Upgraded Telegram Sales Funnel Bot into a complete 3-step Quiz Funnel:
# - CommandStart presents Q1: Experience Level choice using inline keyboards
# - Added handle_q1_selection callback saving Q1 and presenting Q2
# - Added handle_q2_selection callback saving Q2, swapping to image_3 (quiz mid-point) and presenting Q3
# - Added handle_q3_selection callback saving Q3, resolving personalized bonus, setting stage to 2,
#   swapping to image_2 (subscribe prompt) and scheduling nudge
# - Upgraded check_subscription handler to call upgraded scheduler transition
# - Upgraded /admin and /admin_full dashboards to display quiz Q1/Q2/Q3 distributions and top paths
# - Added ChatMemberUpdated block/unblock handler tracking unsubscribe events
# - Added MessageReactionUpdated reaction listener for ERR analytics
# - Added catch-all reply message handler incrementing replies and resetting re-engagement states
# - Upgraded /admin with manager groups rotation mapping
# - Upgraded /admin_full with ERR metrics and re-engagement tracking metrics
