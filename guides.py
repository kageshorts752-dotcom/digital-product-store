"""Original PDF guides for the Digital Product Store.

100 guides in 5 categories, 20 each. Every guide is generated here in pure
Python (stdlib only, no reportlab, no Pillow) so it can be built at import
time on Vercel, where the deployment filesystem is read-only: the caller
writes the bytes into a writable directory (see app.py PRIVATE handling)
instead of relying on a binary file shipped in the repo.

Safety rules baked into every guide:
- General information only, not medical advice; readers are told to consult
  a qualified professional before changing diet, training, or health habits.
- No medical diagnosis or treatment claims, no steroids, no extreme diets,
  no surgery encouragement, no body-dysmorphia framing.
- Mind Mastery is about self-control, focus, discipline and habits only --
  never about manipulating other people. Attractivemaxing is about
  confidence, communication, social skills and presentation, respectfully.
- No copied text, no other creators' brand names.
"""
import os
import textwrap

SELLER = "StudyNest Press"

# Each topic: (slug, title, category, focus, description, practices)
# focus is a short phrase reused inside chapter bullets; practices are
# topic-specific actions used in the routine and chapters.
TOPICS = [
    # ---------------- Bodybuilding (20) ----------------
    ("chest-hypertrophy-basics", "Chest Hypertrophy Basics", "Bodybuilding",
     "chest training",
     "A beginner-friendly guide to building a stronger, fuller chest with safe, progressive training.",
     ["Press twice a week with good form", "Add one fly or cable movement per session",
      "Track your top set weight every week", "Pause briefly at the bottom of each press"]),
    ("back-width-and-thickness", "Back Width and Thickness", "Bodybuilding",
     "back training",
     "How to train your back for width and thickness using pulls, rows, and patient progression.",
     ["Do one vertical pull and one row each session", "Squeeze your shoulder blades on rows",
      "Use a full range of motion on pulldowns", "Add weight only when form stays clean"]),
    ("leg-day-foundations", "Leg Day Foundations", "Bodybuilding",
     "leg training",
     "Build strong legs from the ground up with squats, hinges, and single-leg work.",
     ["Squat once a week with controlled depth", "Hinge once a week for hamstrings and glutes",
      "Add one single-leg movement per session", "Warm up hips and ankles before leg day"]),
    ("shoulder-development-guide", "Shoulder Development Guide", "Bodybuilding",
     "shoulder training",
     "Train all three heads of the shoulder for strength, shape, and healthy joints.",
     ["Press overhead once a week", "Add lateral raises twice a week",
      "Include rear-delt work every session", "Keep presses pain-free and controlled"]),
    ("arm-growth-guide", "Arm Growth: Biceps and Triceps", "Bodybuilding",
     "arm training",
     "A simple, effective plan for bigger arms built on pressing, curling, and steady progression.",
     ["Train triceps after pressing movements", "Curl with a full stretch at the bottom",
      "Add weight slowly on curls and extensions", "Keep elbows still during isolation work"]),
    ("progressive-overload-system", "Progressive Overload System", "Bodybuilding",
     "progressive overload",
     "The system behind lasting muscle growth: do a little more, safely, over time.",
     ["Log every workout in a notebook or app", "Beat last week by one rep or a small weight jump",
      "Deload every 4 to 6 weeks", "Change one variable at a time"]),
    ("beginner-gym-starter-plan", "Beginner Gym Starter Plan", "Bodybuilding",
     "starting at the gym",
     "Your first 8 weeks in the gym, without confusion: what to do, how often, and how to progress.",
     ["Train 3 days a week on non-consecutive days", "Learn 6 basic movements first",
      "Start light and add weight weekly", "Ask gym staff for a form check"]),
    ("home-workout-no-equipment", "Home Workouts Without Equipment", "Bodybuilding",
     "bodyweight training",
     "Build strength at home with bodyweight progressions, no gym or gear required.",
     ["Use push-up, squat, and hinge variations", "Make moves harder by slowing them down",
      "Train 3 to 4 short sessions a week", "Use a chair or wall for support when needed"]),
    ("dumbbell-only-muscle-plan", "Dumbbell-Only Muscle Plan", "Bodybuilding",
     "dumbbell training",
     "A complete muscle plan using only dumbbells, at home or in a small gym.",
     ["Pick weights you can control for 8 to 12 reps", "Do a push, pull, and leg move each session",
      "Rest 60 to 90 seconds between sets", "Buy or use the next weight up when sets feel easy"]),
    ("push-pull-legs-split", "Push Pull Legs Split", "Bodybuilding",
     "training splits",
     "Organise your week into push, pull, and legs days for balanced, recoverable training.",
     ["Train 3 to 6 days a week on this split", "Keep 2 to 4 exercises per muscle group",
      "Put the hardest lift first each day", "Take at least one full rest day a week"]),
    ("upper-lower-split-guide", "Upper Lower Split Guide", "Bodybuilding",
     "training splits",
     "Train upper body and lower body on alternate days for strength and balance.",
     ["Alternate upper and lower days", "Hit each muscle group twice a week",
      "Pair a push with a pull on upper days", "Keep lower days to squat, hinge, and one accessory"]),
    ("full-body-strength-routine", "Full Body Strength Routine", "Bodybuilding",
     "full-body training",
     "One routine that trains everything, three days a week, for busy lifters.",
     ["Do one squat, one push, and one pull per session", "Use 3 sets of 5 to 8 reps on main lifts",
      "Rest 2 to 3 minutes on heavy sets", "Add a core movement at the end"]),
    ("core-strength-and-abs", "Core Strength and Abs", "Bodybuilding",
     "core training",
     "Build a strong, useful core for lifting, posture, and everyday movement.",
     ["Train anti-rotation and anti-extension moves", "Brace your core before every lift",
      "Add core work 2 to 3 times a week", "Pair core work with breathing control"]),
    ("glute-training-guide", "Glute Training Guide", "Bodybuilding",
     "glute training",
     "Train your glutes for strength, posture, and athletic movement, with or without a gym.",
     ["Hip thrust or bridge twice a week", "Add a single-leg glute move each session",
      "Squeeze at the top of every rep", "Warm up glutes before squats and hinges"]),
    ("mobility-for-lifters", "Mobility for Lifters", "Bodybuilding",
     "mobility",
     "Stay mobile enough to lift well: hips, shoulders, ankles, and thoracic spine.",
     ["Spend 5 minutes on mobility before training", "Work hips and ankles on leg days",
      "Work shoulders and upper back on push days", "Hold stretches 30 to 60 seconds, pain-free"]),
    ("workout-recovery-basics", "Workout Recovery Basics", "Bodybuilding",
     "recovery",
     "Recover well so you can train again: sleep, food, rest days, and smart deloads.",
     ["Sleep 7 to 9 hours most nights", "Eat enough protein across the day",
      "Take 1 to 2 rest days a week", "Deload when performance drops for a week"]),
    ("protein-and-muscle-nutrition", "Protein and Muscle Nutrition", "Bodybuilding",
     "muscle nutrition",
     "General nutrition basics for muscle building, without fad diets or extreme rules.",
     ["Include a protein food at each meal", "Eat mostly whole foods most of the time",
      "Drink water through the day", "Keep meals regular around training"]),
    ("cutting-without-losing-muscle", "Cutting Without Losing Muscle", "Bodybuilding",
     "fat loss while keeping muscle",
     "A steady, sensible approach to losing fat while keeping the muscle you built.",
     ["Keep lifting heavy while eating a little less", "Keep protein steady at each meal",
      "Lose weight slowly, not crash-diet", "Walk daily for extra activity"]),
    ("bulking-the-sensible-way", "Bulking the Sensible Way", "Bodybuilding",
     "muscle gain nutrition",
     "Gain muscle with a small, steady surplus and honest tracking, not force-feeding.",
     ["Eat a small surplus, not a huge one", "Track weight weekly, not daily",
      "Keep training hard while you gain", "Adjust food up or down by small steps"]),
    ("form-first-lifting-guide", "Form-First Lifting Guide", "Bodybuilding",
     "lifting form",
     "Lift safely for years: set-up, bracing, range of motion, and knowing when to stop.",
     ["Film one set a week to check form", "Start every lift with a tight brace",
      "Use a full, controlled range of motion", "Stop a set when form breaks down"]),
    # ---------------- Mind Mastery (20) ----------------
    ("deep-focus-work-system", "Deep Focus Work System", "Mind Mastery",
     "deep focus",
     "Do your hardest work in focused blocks, with distractions handled before you start.",
     ["Work in 25 to 50 minute focused blocks", "Put your phone in another room",
      "Define one clear outcome before each block", "Take a real break between blocks"]),
    ("digital-detox-starter", "Digital Detox Starter", "Mind Mastery",
     "reducing screen time",
     "Reclaim attention from endless scrolling with a gentle, realistic detox plan.",
     ["Set one phone-free hour a day", "Remove one distracting app for a week",
      "Charge your phone outside the bedroom", "Replace scrolling with one offline activity"]),
    ("morning-routine-builder", "Morning Routine Builder", "Mind Mastery",
     "morning routines",
     "Build a morning that starts your day with intention instead of reaction.",
     ["Wake at a consistent time", "Avoid your phone for the first 20 minutes",
      "Do one small win first: water, light, movement", "Write your top 3 tasks for the day"]),
    ("habit-stacking-guide", "Habit Stacking Guide", "Mind Mastery",
     "habit building",
     "Attach new habits to habits you already do, so they stick without willpower battles.",
     ["Pick one existing daily anchor habit", "Attach the new habit right after it",
      "Keep the new habit under 2 minutes at first", "Track it daily with a simple tick"]),
    ("breaking-procrastination", "Breaking Procrastination", "Mind Mastery",
     "beating procrastination",
     "Start hard tasks sooner with smaller first steps, clear deadlines, and less friction.",
     ["Shrink the task to a 2-minute first step", "Set a visible start time, not just a deadline",
      "Remove the biggest distraction first", "Reward finishing, not just starting"]),
    ("self-discipline-daily-system", "Self-Discipline Daily System", "Mind Mastery",
     "self-discipline",
     "Discipline as a system: environment, routines, and recovery, not just willpower.",
     ["Design your environment before relying on willpower", "Keep one non-negotiable daily habit",
      "Plan for temptations in advance", "Forgive a slip and restart the next day"]),
    ("attention-training-basics", "Attention Training Basics", "Mind Mastery",
     "attention",
     "Train your attention like a muscle: single-tasking, noticing drift, and returning.",
     ["Do one task at a time, on purpose", "Notice when your mind wanders, without judgment",
      "Return to the task gently, every time", "Practise 5 minutes of focused attention daily"]),
    ("overstimulation-reset-basics", "Overstimulation Reset Basics", "Mind Mastery",
     "reducing overstimulation",
     "A calm, general guide to lowering constant stimulation so focus feels easier again.",
     ["Take one low-stimulation walk a day", "Cut background noise and autoplay",
      "Keep one boring, quiet hour a week", "Choose one input at a time: read, or listen, not both"]),
    ("goal-setting-that-sticks", "Goal Setting That Sticks", "Mind Mastery",
     "goal setting",
     "Set goals you can actually follow: clear, measurable, reviewed weekly.",
     ["Write goals in specific, measurable words", "Break each goal into weekly actions",
      "Review progress every Sunday", "Adjust the plan, not the goal, when stuck"]),
    ("journaling-for-clarity", "Journaling for Clarity", "Mind Mastery",
     "journaling",
     "Use short daily journaling to clear your mind, spot patterns, and decide better.",
     ["Write 5 minutes a day, no rules", "Ask: what went well, what was hard, what is next",
      "Review old entries monthly", "Keep a separate list for worries and ideas"]),
    ("meditation-for-beginners", "Meditation for Beginners", "Mind Mastery",
     "meditation",
     "Start meditation simply: short sits, gentle attention, no special equipment.",
     ["Sit for 5 minutes a day to start", "Focus on your breath, return when distracted",
      "Sit in the same place and time daily", "Increase by 1 minute a week if it helps"]),
    ("beating-phone-distraction", "Beating Phone Distraction", "Mind Mastery",
     "phone distraction",
     "Take back your day from your phone with limits, friction, and better defaults.",
     ["Turn off non-essential notifications", "Use grayscale or app timers if they help",
      "Keep the phone out of reach during work", "Set app-free zones: meals, mornings, bedtime"]),
    ("willpower-and-temptation-plan", "Willpower and Temptation Plan", "Mind Mastery",
     "handling temptation",
     "Handle temptation with planning, not fighting: avoid, delay, and substitute.",
     ["Name your top 3 temptations in advance", "Make the tempting thing harder to reach",
      "Delay by 10 minutes before giving in", "Have a ready substitute action"]),
    ("time-blocking-mastery", "Time Blocking Mastery", "Mind Mastery",
     "time blocking",
     "Plan your day in blocks so important work gets a time, not just a to-do list entry.",
     ["Block your hardest task first", "Leave buffer blocks between meetings",
      "Review and re-plan blocks each evening", "Protect one block a day from interruptions"]),
    ("evening-review-routine", "Evening Review Routine", "Mind Mastery",
     "evening routines",
     "End the day well: review, plan tomorrow, and wind down for better sleep.",
     ["Write tomorrow's top 3 tasks at night", "Note one win from today",
      "Prepare clothes and bag the night before", "Dim screens an hour before bed"]),
    ("reading-habit-builder", "Reading Habit Builder", "Mind Mastery",
     "reading habits",
     "Read more without forcing it: small daily pages, good books, and a reading spot.",
     ["Read 10 pages a day to start", "Keep a book where you usually scroll",
      "Choose books you actually enjoy", "Note one idea from each reading session"]),
    ("learning-faster-study-system", "Learning Faster Study System", "Mind Mastery",
     "studying and learning",
     "Learn faster with active recall, spacing, and practice, not just re-reading.",
     ["Test yourself before re-reading notes", "Space revision over days, not one cram session",
      "Teach the idea to someone else", "Practise with real problems, not just highlights"]),
    ("stress-management-basics", "Stress Management Basics", "Mind Mastery",
     "managing stress",
     "General, everyday ways to lower stress: movement, rest, limits, and talking it out.",
     ["Move your body daily, even briefly", "Keep sleep and meals regular under stress",
      "Say no to one extra commitment a week", "Talk to someone you trust when stressed"]),
    ("confidence-through-action", "Confidence Through Action", "Mind Mastery",
     "self-confidence",
     "Build confidence by doing small hard things repeatedly, not by waiting to feel ready.",
     ["Do one small brave action daily", "Keep promises you make to yourself",
      "Track evidence of what you handled", "Compare yourself to your past self, not others"]),
    ("consistency-over-motivation", "Consistency Over Motivation", "Mind Mastery",
     "consistency",
     "Stay consistent when motivation fades: minimums, tracking, and restart rules.",
     ["Set a minimum version for bad days", "Track streaks, but never miss twice",
      "Make the habit easy to start", "Review weekly and fix the friction, not yourself"]),
]

TOPICS += [
    # ---------------- Healthmax (20) ----------------
    ("sleep-better-starter-guide", "Sleep Better Starter Guide", "Healthmax",
     "better sleep",
     "General habits for better sleep: light, timing, wind-down, and a calm bedroom.",
     ["Keep a consistent wake time", "Dim lights an hour before bed",
      "Keep your bedroom cool, dark, and quiet", "Avoid heavy meals late at night"]),
    ("morning-sunlight-and-energy", "Morning Sunlight and Energy", "Healthmax",
     "morning energy",
     "Use morning light, movement, and a steady start to feel more awake naturally.",
     ["Get daylight soon after waking", "Move for 5 minutes in the morning",
      "Drink water first thing", "Eat a balanced breakfast most days"]),
    ("walking-habit-guide", "Walking Habit Guide", "Healthmax",
     "daily walking",
     "Build a daily walking habit for energy, mood, and general health, at any fitness level.",
     ["Walk 10 minutes after one meal a day", "Add 5 minutes a week until it feels easy",
      "Walk with a friend or podcast when possible", "Keep comfortable shoes by the door"]),
    ("hydration-basics", "Hydration Basics", "Healthmax",
     "hydration",
     "Simple, general hydration habits for everyday life, work, and exercise.",
     ["Keep water visible at your desk", "Drink a glass with each meal",
      "Drink more on hot days and after exercise", "Watch for thirst and dark urine as cues"]),
    ("balanced-plate-basics", "Balanced Plate Basics", "Healthmax",
     "balanced eating",
     "Build balanced meals with vegetables, protein, whole grains, and healthy fats.",
     ["Fill half your plate with vegetables", "Include a protein food at each meal",
      "Choose whole grains most of the time", "Add fruit for snacks instead of sweets"]),
    ("home-cooking-starter", "Home Cooking Starter", "Healthmax",
     "home cooking",
     "Cook more at home with simple meals, batch cooking, and a stocked pantry.",
     ["Learn 5 simple meals by heart", "Cook double and save half for tomorrow",
      "Keep frozen vegetables and grains on hand", "Prep ingredients once for the week"]),
    ("sugar-and-snack-swaps", "Sugar and Snack Swaps", "Healthmax",
     "healthier snacking",
     "General swaps that cut added sugar without feeling deprived or extreme.",
     ["Swap sugary drinks for water or sparkling water", "Keep fruit and nuts as default snacks",
      "Read labels for added sugar", "Allow treats on purpose, not by accident"]),
    ("gut-friendly-eating-basics", "Gut-Friendly Eating Basics", "Healthmax",
     "digestive comfort",
     "General eating habits that support everyday digestive comfort. Not medical advice.",
     ["Eat slowly and chew well", "Include fibre-rich foods gradually",
      "Include fermented foods if you enjoy them", "Note foods that bother you and discuss them with a professional"]),
    ("posture-and-desk-health", "Posture and Desk Health", "Healthmax",
     "desk posture",
     "Sit, stand, and move better at a desk to reduce everyday stiffness and strain.",
     ["Set your screen at eye level", "Stand or walk every 30 to 60 minutes",
      "Do one stretch break per work block", "Keep feet flat and shoulders relaxed"]),
    ("stretching-daily-routine", "Stretching Daily Routine", "Healthmax",
     "daily stretching",
     "A short daily stretching routine for flexibility, comfort, and easy movement.",
     ["Stretch 5 to 10 minutes a day", "Hold each stretch 30 seconds, pain-free",
      "Stretch hips, chest, and hamstrings daily", "Breathe slowly during every stretch"]),
    ("breathing-and-calm-basics", "Breathing and Calm Basics", "Healthmax",
     "calm breathing",
     "General breathing practices for calm and focus in everyday stressful moments.",
     ["Breathe slowly through your nose", "Try 4 seconds in, 4 seconds out",
      "Use slow breathing before stressful moments", "Practise 2 minutes a day when calm"]),
    ("sunlight-and-vitamin-basics", "Sunlight and Vitamin Basics", "Healthmax",
     "sunlight and nutrition",
     "General information about sunlight, diet, and everyday nutrition. Talk to a professional about supplements.",
     ["Get regular daylight exposure", "Eat a varied diet with vegetables and whole foods",
      "Do not self-prescribe high-dose supplements", "Ask a professional if you have concerns"]),
    ("weight-management-basics", "Weight Management Basics", "Healthmax",
     "weight management",
     "A steady, general approach to weight: regular meals, movement, sleep, and patience.",
     ["Eat regular, balanced meals", "Move daily and lift or walk often",
      "Sleep 7 to 9 hours most nights", "Track trends weekly, not daily swings"]),
    ("heart-healthy-movement", "Heart-Healthy Movement", "Healthmax",
     "heart-healthy activity",
     "General activity habits that support heart health over a lifetime. Not medical advice.",
     ["Walk briskly most days", "Add 2 days of strength work a week",
      "Break up long sitting periods", "Build activity gradually over weeks"]),
    ("joint-friendly-exercise", "Joint-Friendly Exercise", "Healthmax",
     "joint-friendly movement",
     "Move more while being kind to your joints: low-impact options and smart progression.",
     ["Choose walking, cycling, or swimming often", "Warm up before every session",
      "Increase load by small steps", "Stop if pain is sharp or swelling appears"]),
    ("energy-without-caffeine-overload", "Energy Without Caffeine Overload", "Healthmax",
     "natural energy",
     "General ways to feel more energetic without relying on endless caffeine.",
     ["Keep caffeine to mornings where possible", "Sleep and daylight first, caffeine second",
      "Move briefly when energy dips", "Eat balanced meals instead of skipping them"]),
    ("screen-time-and-eye-comfort", "Screen Time and Eye Comfort", "Healthmax",
     "eye comfort",
     "Reduce eye strain and screen fatigue with breaks, distance, and good lighting.",
     ["Follow the 20-20-20 rule for breaks", "Keep screens at arm's length",
      "Blink fully and often", "Match screen brightness to the room"]),
    ("travel-health-basics", "Travel Health Basics", "Healthmax",
     "healthy travel",
     "Stay healthy on trips: sleep, water, movement, and simple food choices.",
     ["Walk and stretch during long trips", "Carry water and simple snacks",
      "Keep sleep as regular as possible", "Wash hands often while travelling"]),
    ("everyday-immunity-habits", "Everyday Immunity Habits", "Healthmax",
     "everyday health habits",
     "General lifestyle habits that support everyday health. Not a treatment or guarantee.",
     ["Sleep regularly and eat varied meals", "Move daily and manage stress",
      "Wash hands and keep up with routine care", "Stay home when you feel unwell"]),
    ("healthy-aging-habits", "Healthy Aging Habits", "Healthmax",
     "healthy aging",
     "General habits for aging well: strength, balance, learning, and connection.",
     ["Strength train twice a week", "Practise balance a few minutes a day",
      "Keep learning something new", "Stay socially connected regularly"]),
    # ---------------- Lookmaxing (20) ----------------
    ("skincare-basics-for-beginners", "Skincare Basics for Beginners", "Lookmaxing",
     "skincare",
     "Start skincare simply: cleanse, moisturise, and protect, without a 10-step routine.",
     ["Wash gently morning and night", "Moisturise after washing",
      "Use sunscreen daily", "Introduce one new product at a time"]),
    ("clear-skin-daily-routine", "Clear Skin Daily Routine", "Lookmaxing",
     "clear skin habits",
     "General daily habits for clearer-looking skin. See a professional for persistent skin concerns.",
     ["Keep your routine simple and consistent", "Do not pick or squeeze spots",
      "Change pillowcases regularly", "Remove makeup before bed"]),
    ("hair-care-and-styling-basics", "Hair Care and Styling Basics", "Lookmaxing",
     "hair care",
     "Keep hair healthy and styled with washing, conditioning, and simple styling habits.",
     ["Wash as often as your hair type needs", "Condition the lengths, not just the roots",
      "Avoid very hot tools daily", "Trim regularly to remove split ends"]),
    ("beard-grooming-guide", "Beard Grooming Guide", "Lookmaxing",
     "beard grooming",
     "Keep a beard clean, shaped, and comfortable with simple daily care.",
     ["Wash your beard regularly", "Oil or balm daily to reduce dryness",
      "Trim neckline and cheek lines weekly", "Brush daily to train growth direction"]),
    ("clean-shaving-guide", "Clean Shaving Guide", "Lookmaxing",
     "shaving",
     "Shave comfortably with prep, sharp tools, and calm aftercare.",
     ["Shave after a warm shower", "Use a sharp blade and light pressure",
      "Shave with the grain first", "Rinse with cool water and moisturise"]),
    ("personal-style-foundations", "Personal Style Foundations", "Lookmaxing",
     "personal style",
     "Build a personal style that fits your life, budget, and body, without chasing trends.",
     ["Define 3 words for your style", "Buy clothes that fit well first",
      "Build around neutral basics", "Add one personality piece at a time"]),
    ("dressing-for-your-body-type", "Dressing for Your Body Type", "Lookmaxing",
     "dressing well",
     "Dress with confidence: fit, proportion, and comfort for your own body.",
     ["Prioritise fit over brand or trend", "Balance proportions: fitted with relaxed",
      "Wear clothes you can move in", "Tailor key pieces if the fit is close"]),
    ("colour-and-wardrobe-basics", "Colour and Wardrobe Basics", "Lookmaxing",
     "colour and wardrobe",
     "Use colour simply: neutrals, one accent, and combinations you feel good in.",
     ["Build a neutral base wardrobe", "Add one accent colour at a time",
      "Match leathers and metals", "Try colours in daylight before buying"]),
    ("posture-and-presence", "Posture and Presence", "Lookmaxing",
     "posture",
     "Stand and move with presence: tall posture, relaxed shoulders, and easy movement.",
     ["Stand tall with shoulders relaxed", "Strengthen your back and core",
      "Stretch your chest and hip flexors", "Walk at a calm, steady pace"]),
    ("smile-and-dental-care-basics", "Smile and Dental Care Basics", "Lookmaxing",
     "dental care",
     "General dental hygiene habits for a healthy smile. See a dentist for check-ups.",
     ["Brush twice a day with fluoride toothpaste", "Clean between teeth daily",
      "Limit sugary drinks", "Visit a dentist regularly"]),
    ("fragrance-basics", "Fragrance Basics", "Lookmaxing",
     "fragrance",
     "Wear fragrance well: light, appropriate, and never overpowering.",
     ["Apply 1 to 2 sprays only", "Spray on skin, not clothes, where possible",
      "Choose lighter scents for daytime", "Store fragrance away from heat and light"]),
    ("nail-and-hand-care", "Nail and Hand Care", "Lookmaxing",
     "hand and nail care",
     "Keep hands and nails clean and neat with a few minutes a week.",
     ["Trim nails weekly", "Moisturise hands daily",
      "Push cuticles back gently, never cut deeply", "Wear gloves for harsh cleaning"]),
    ("eyebrow-grooming-basics", "Eyebrow Grooming Basics", "Lookmaxing",
     "eyebrow grooming",
     "Keep brows neat and natural: clean up strays, keep your natural shape.",
     ["Follow your natural brow shape", "Tweeze strays only, in good light",
      "Trim long hairs with a small comb", "Do less than you think you need"]),
    ("photo-ready-grooming", "Photo-Ready Grooming", "Lookmaxing",
     "looking good in photos",
     "Look your best in photos with grooming, light, posture, and a relaxed expression.",
     ["Groom the day before, not minutes before", "Face soft daylight for photos",
      "Relax your shoulders and jaw", "Practise a natural, relaxed smile"]),
    ("seasonal-wardrobe-planner", "Seasonal Wardrobe Planner", "Lookmaxing",
     "seasonal wardrobe",
     "Plan your wardrobe by season so you always have something suitable to wear.",
     ["Audit your wardrobe each season", "List gaps before you shop",
      "Store out-of-season clothes cleanly", "Buy versatile layers, not one-off pieces"]),
    ("capsule-wardrobe-builder", "Capsule Wardrobe Builder", "Lookmaxing",
     "capsule wardrobe",
     "Build a small wardrobe where everything works together, saving time and money.",
     ["Pick 20 to 30 versatile pieces", "Choose a shared colour palette",
      "Make sure every top matches 3 bottoms", "Replace worn pieces one at a time"]),
    ("skin-type-basics", "Skin Type Basics", "Lookmaxing",
     "skin types",
     "General guidance on understanding your skin type and choosing suitable products.",
     ["Observe how your skin feels after washing", "Choose gentle products for sensitive skin",
      "Use lighter products for oily-feeling skin", "Patch-test new products first"]),
    ("haircut-communication-guide", "Haircut Communication Guide", "Lookmaxing",
     "communicating with your barber",
     "Get the haircut you want by showing references and describing it clearly.",
     ["Bring 2 to 3 reference photos", "Describe length in centimetres, not just short",
      "Say what you do not want, too", "Ask for styling tips before you leave"]),
    ("daily-grooming-checklist", "Daily Grooming Checklist", "Lookmaxing",
     "daily grooming",
     "A 10-minute daily grooming checklist that keeps you looking polished every day.",
     ["Wash, moisturise, and protect skin", "Style hair and check your beard",
      "Check nails, teeth, and clothes", "Add fragrance lightly, if you wear it"]),
    ("confidence-through-grooming", "Confidence Through Grooming", "Lookmaxing",
     "grooming and self-care",
     "Use grooming as self-care that supports confidence, without chasing perfection.",
     ["Keep one daily self-care ritual", "Dress for the day you want",
      "Focus on health and cleanliness, not flaws", "Celebrate consistency, not perfection"]),
    # ---------------- Attractivemaxing (20) ----------------
    ("confidence-building-basics", "Confidence Building Basics", "Attractivemaxing",
     "confidence",
     "Build real confidence through small wins, preparation, and self-respect.",
     ["Do one small brave thing daily", "Prepare for situations that scare you",
      "Keep promises to yourself", "Speak kindly to yourself after setbacks"]),
    ("conversation-skills-starter", "Conversation Skills Starter", "Attractivemaxing",
     "conversation",
     "Start and hold conversations with ease: openers, questions, and genuine interest.",
     ["Open with something in the situation", "Ask open questions, then listen",
      "Share a little, then ask again", "End warmly and remember names"]),
    ("body-language-basics", "Body Language Basics", "Attractivemaxing",
     "body language",
     "Communicate warmth and confidence with relaxed posture, eye contact, and gestures.",
     ["Stand open, arms uncrossed", "Make comfortable eye contact",
      "Mirror the other person's energy gently", "Smile genuinely when greeting people"]),
    ("first-impressions-guide", "First Impressions Guide", "Attractivemaxing",
     "first impressions",
     "Make strong first impressions with grooming, warmth, and clear communication.",
     ["Arrive on time and well-groomed", "Greet by name with a warm smile",
      "Listen more than you talk at first", "Follow up after meeting someone new"]),
    ("public-speaking-confidence", "Public Speaking Confidence", "Attractivemaxing",
     "public speaking",
     "Speak in public with less fear: preparation, practice, and simple delivery.",
     ["Practise out loud, not just in your head", "Open with one clear point",
      "Speak slowly and pause", "Practise in front of one trusted person first"]),
    ("making-friends-as-an-adult", "Making Friends as an Adult", "Attractivemaxing",
     "making friends",
     "Make friends as an adult with repeated contact, shared activities, and initiative.",
     ["Join a regular group or activity", "Show up consistently, even when shy",
      "Invite someone for coffee after meeting twice", "Be the one who follows up"]),
    ("dating-confidence-basics", "Dating Confidence Basics", "Attractivemaxing",
     "dating with confidence",
     "Approach dating with confidence, respect, and clear communication. Always respect consent and boundaries.",
     ["Be clear and honest about intentions", "Respect a no the first time",
      "Plan simple, low-pressure first dates", "Focus on getting to know the person"]),
    ("storytelling-and-charisma", "Storytelling and Charisma", "Attractivemaxing",
     "storytelling",
     "Tell stories people enjoy: short, vivid, with a point, and room for others.",
     ["Keep stories short and vivid", "Start in the middle of the action",
      "Show feeling, not just facts", "End with a question or a laugh"]),
    ("listening-skills-mastery", "Listening Skills Mastery", "Attractivemaxing",
     "listening",
     "Become someone people love talking to by listening fully and responding thoughtfully.",
     ["Put your phone away when listening", "Reflect back what you heard",
      "Ask follow-up questions", "Do not interrupt to tell your own story"]),
    ("humour-and-lightness", "Humour and Lightness", "Attractivemaxing",
     "light humour",
     "Use light, kind humour to make social moments easier, without mocking anyone.",
     ["Laugh at yourself first", "Keep jokes kind and inclusive",
      "Use humour to ease tension, not to win", "Notice what makes others laugh"]),
    ("networking-without-awkwardness", "Networking Without Awkwardness", "Attractivemaxing",
     "networking",
     "Network naturally: give value, ask good questions, and follow up kindly.",
     ["Prepare one line about what you do", "Ask what others are working on",
      "Offer help before asking for it", "Follow up within 2 days"]),
    ("handling-rejection-gracefully", "Handling Rejection Gracefully", "Attractivemaxing",
     "handling rejection",
     "Handle rejection with grace: separate the outcome from your worth, learn, and move on.",
     ["Let yourself feel disappointed briefly", "Ask what you can learn, if appropriate",
      "Do not chase or argue after a no", "Try again elsewhere with what you learned"]),
    ("social-anxiety-basics", "Social Anxiety Basics", "Attractivemaxing",
     "social confidence",
     "General strategies for social confidence. If anxiety is severe, consider talking to a professional.",
     ["Start with low-pressure social settings", "Prepare one opener in advance",
      "Focus on the other person, not yourself", "Gradually increase social challenges"]),
    ("personal-brand-and-presence", "Personal Brand and Presence", "Attractivemaxing",
     "personal presence",
     "Build a personal presence that matches who you are, online and in person.",
     ["Decide 3 values you want to be known for", "Keep your online presence consistent",
      "Share work and ideas regularly", "Be reliable: do what you say"]),
    ("voice-and-speaking-clarity", "Voice and Speaking Clarity", "Attractivemaxing",
     "speaking clearly",
     "Speak clearly and confidently: pace, volume, breathing, and warm tone.",
     ["Slow down by 20 percent", "Breathe from your diaphragm",
      "Project your voice to the back of the room", "Record yourself once a week to check"]),
    ("eye-contact-and-warmth", "Eye Contact and Warmth", "Attractivemaxing",
     "warmth and eye contact",
     "Use warm eye contact and a relaxed face to make people feel welcome.",
     ["Look at the other person when greeting", "Hold eye contact for a few seconds, then glance away naturally",
      "Smile with your eyes, not just your mouth", "Match your expression to the conversation"]),
    ("compliment-and-kindness-guide", "Compliment and Kindness Guide", "Attractivemaxing",
     "genuine compliments",
     "Give compliments that feel genuine: specific, sincere, and respectful.",
     ["Compliment effort and choices, not just looks", "Be specific: name what you noticed",
      "Keep it brief and warm", "Accept compliments gracefully, too"]),
    ("group-conversation-skills", "Group Conversation Skills", "Attractivemaxing",
     "group conversations",
     "Join and enjoy group conversations: enter gracefully, include others, and share the floor.",
     ["Join a group with a comment on the topic", "Include quieter people with a question",
      "Share airtime: speak, then listen", "Remember details for next time"]),
    ("texting-and-online-communication", "Texting and Online Communication", "Attractivemaxing",
     "online communication",
     "Communicate well online: clear messages, good timing, and respect for boundaries.",
     ["Be clear and warm in messages", "Do not double-text anxiously",
      "Match the other person's reply pace", "Move important talks to voice or in person"]),
    ("becoming-more-approachable", "Becoming More Approachable", "Attractivemaxing",
     "being approachable",
     "Become more approachable with open body language, warmth, and availability.",
     ["Keep your phone away in social settings", "Smile and greet people first",
      "Stand where others can join you", "Ask others about themselves first"]),
]

# ---------------- Category chapter templates ----------------
# {focus} and {title} are filled per topic. Bullets are general, safe advice.
CHAPTERS = {
    "Bodybuilding": [
        ("Chapter 1: Foundations", [
            "Start with the basics of {focus} before adding complexity.",
            "Learn correct form with light weights, then progress slowly.",
            "Train consistently 3 to 4 times a week rather than in bursts.",
            "Warm up for 5 to 10 minutes before every session.",
        ]),
        ("Chapter 2: Building Your Routine", [
            "Choose 4 to 6 exercises that cover the main movements for {focus}.",
            "Use 3 to 4 sets of 6 to 12 reps for most muscle-building work.",
            "Rest 60 to 120 seconds between sets, longer on heavy lifts.",
            "Put the hardest exercise first, when you are freshest.",
        ]),
        ("Chapter 3: Progression That Lasts", [
            "Add weight, reps, or sets in small steps, week by week.",
            "Track every session so progress is visible, not guessed.",
            "When progress stalls for 2 weeks, change one variable only.",
            "Take a lighter week every 4 to 6 weeks to recover fully.",
        ]),
        ("Chapter 4: Recovery and Everyday Habits", [
            "Sleep 7 to 9 hours most nights; recovery is when growth happens.",
            "Eat regular, balanced meals with a protein food at each meal.",
            "Drink water through the day, especially around training.",
            "Take rest days seriously; more training is not always better.",
        ]),
        ("Chapter 5: Staying Safe and Consistent", [
            "Stop a set if pain is sharp, sudden, or joint-related.",
            "Never sacrifice form to lift a heavier weight.",
            "Warm up the specific joints and muscles you will train.",
            "If you are unsure about a movement, ask a qualified coach.",
        ]),
    ],
    "Mind Mastery": [
        ("Chapter 1: How Attention Works", [
            "Attention is limited: one clear task at a time beats multitasking.",
            "Distractions are usually environmental, not a character flaw.",
            "A clear next action makes starting much easier.",
            "Short, regular practice beats rare, heroic efforts.",
        ]),
        ("Chapter 2: Designing Your Environment", [
            "Remove the biggest distraction before you start work on {focus}.",
            "Keep the tools you need visible and distractions out of sight.",
            "Use a dedicated place and time for focused work when possible.",
            "Tell others when you are in a focus block, if you can.",
        ]),
        ("Chapter 3: Daily Systems Over Willpower", [
            "Build {focus} into a daily routine at a fixed time.",
            "Start with a version so small you cannot fail it.",
            "Track the habit daily with a simple tick or calendar mark.",
            "If you miss a day, restart the next day without guilt.",
        ]),
        ("Chapter 4: Handling Setbacks", [
            "A slip is data, not failure: note what triggered it.",
            "Fix the trigger (time, place, or cue) rather than blaming yourself.",
            "Keep a minimum version of the habit for difficult days.",
            "Review weekly: what worked, what got in the way, what to change.",
        ]),
        ("Chapter 5: Making It Last", [
            "Increase difficulty slowly, only when the current level feels easy.",
            "Pair the habit with something you already enjoy.",
            "Share your goal with one person who will check in kindly.",
            "Celebrate consistency at 7, 30, and 90 days.",
        ]),
    ],
    "Healthmax": [
        ("Chapter 1: The Basics That Matter Most", [
            "Sleep, movement, balanced food, and water cover most of {focus}.",
            "Small, daily habits beat perfect weeks followed by giving up.",
            "Change one habit at a time so it actually sticks.",
            "This guide is general information only, not medical advice.",
        ]),
        ("Chapter 2: Building a Daily Rhythm", [
            "Keep wake and sleep times fairly consistent, even on weekends.",
            "Anchor healthy habits to things you already do daily.",
            "Plan meals and movement the day before when you can.",
            "Keep healthy options visible and easy to reach.",
        ]),
        ("Chapter 3: Movement and Energy", [
            "Move a little every day: walking counts, and it adds up.",
            "Add strength or flexibility work 2 to 3 times a week.",
            "Break up long sitting periods with short walks or stretches.",
            "Increase activity gradually; soreness for days means you went too far.",
        ]),
        ("Chapter 4: Food and Drink, Simply", [
            "Build meals around vegetables, protein, and whole grains.",
            "Drink water regularly and limit sugary drinks.",
            "Eat slowly and stop when comfortably full.",
            "Allow favourite foods on purpose; rigid rules rarely last.",
        ]),
        ("Chapter 5: Rest, Stress, and Check-Ins", [
            "Protect sleep like an appointment: same time, dark room, wind-down.",
            "Use movement, breathing, and talking to ease everyday stress.",
            "Notice patterns: what helps your energy, what drains it.",
            "See a qualified professional for persistent or worrying symptoms.",
        ]),
    ],
    "Lookmaxing": [
        ("Chapter 1: Start With Clean and Healthy", [
            "Good grooming starts with cleanliness, health, and consistency.",
            "A simple routine done daily beats a complex routine done rarely.",
            "Choose gentle products first; strong products can irritate skin.",
            "This guide is about self-care and presentation, not perfection.",
        ]),
        ("Chapter 2: Your Daily Routine", [
            "Build a short morning and evening routine for {focus}.",
            "Do the routine at the same time each day until it is automatic.",
            "Keep tools clean: wash brushes, replace blades, clean applicators.",
            "Track what works for you and drop what does not.",
        ]),
        ("Chapter 3: Style and Fit", [
            "Fit matters more than price or brand for {focus}.",
            "Choose clothes and styles that suit your life and comfort.",
            "Keep a simple colour palette and add accents slowly.",
            "Ask a trusted person for honest feedback on fit.",
        ]),
        ("Chapter 4: Posture and Presentation", [
            "Stand tall, shoulders relaxed, head level for {focus}.",
            "Strengthen your back and stretch your chest regularly.",
            "Walk at a calm pace and make comfortable eye contact.",
            "Presentation is about care, not about hiding who you are.",
        ]),
        ("Chapter 5: Maintaining It Long Term", [
            "Schedule regular trims, replacements, and wardrobe checks.",
            "Replace products when they expire or stop working.",
            "Keep a small grooming kit for travel and busy days.",
            "Review your routine seasonally and adjust for weather and lifestyle.",
        ]),
    ],
    "Attractivemaxing": [
        ("Chapter 1: Confidence From the Inside Out", [
            "Confidence grows from preparation, practice, and small wins.",
            "Focus on being genuinely interested in others, not on impressing them.",
            "Good grooming, posture, and clear speech support {focus}.",
            "Everyone feels nervous sometimes; preparation lowers it.",
        ]),
        ("Chapter 2: Communication Basics", [
            "Listen fully before replying; people notice and appreciate it.",
            "Ask open questions and follow up on answers.",
            "Speak clearly, slowly, and warmly.",
            "Share honestly, in small amounts at first, and build trust over time.",
        ]),
        ("Chapter 3: Social Skills in Practice", [
            "Practise {focus} in low-pressure settings first.",
            "Join regular groups where you see the same people repeatedly.",
            "Be the person who initiates plans and follows up.",
            "Include quieter people; it makes you more liked and respected.",
        ]),
        ("Chapter 4: Respect and Boundaries", [
            "Respect every no, boundary, and change of mind immediately.",
            "Compliments should be specific, sincere, and never pushy.",
            "Never use tricks or pressure to influence other people.",
            "Kindness and reliability attract more than any technique.",
        ]),
        ("Chapter 5: Growing Over Time", [
            "Review social moments kindly: what went well, what to try next.",
            "Keep promises, big and small, to build trust.",
            "Learn from rejection without making it about your worth.",
            "Stay consistent: show up, be kind, and keep improving slowly.",
        ]),
    ],
}

MISTAKES = {
    "Bodybuilding": [
        "Skipping warm-ups and jumping straight to heavy weights.",
        "Adding weight while form is breaking down.",
        "Training the same muscles hard every day without rest.",
        "Copying an advanced routine as a beginner.",
        "Ignoring pain and training through sharp joint pain.",
        "Changing the whole routine every week instead of progressing one.",
    ],
    "Mind Mastery": [
        "Trying to change ten habits at once.",
        "Relying on motivation instead of a system and environment.",
        "Setting a huge daily target and quitting after one missed day.",
        "Keeping distractions within arm's reach during focus time.",
        "Judging yourself harshly for a normal lapse in attention.",
        "Never reviewing what actually worked or failed.",
    ],
    "Healthmax": [
        "Following extreme diets or cutting out whole food groups suddenly.",
        "Trying to fix sleep, food, and exercise all in one week.",
        "Ignoring persistent symptoms instead of seeing a professional.",
        "Taking high-dose supplements without professional advice.",
        "Going from no activity to very intense activity overnight.",
        "Judging progress by one bad day instead of a weekly trend.",
    ],
    "Lookmaxing": [
        "Chasing perfection or comparing yourself to edited photos.",
        "Using many strong products at once and irritating your skin.",
        "Considering surgery or extreme measures for normal features.",
        "Copying a style that does not fit your life or comfort.",
        "Skipping basics like sleep, water, and cleanliness for quick fixes.",
        "Over-grooming: over-plucking, over-trimming, or over-styling.",
    ],
    "Attractivemaxing": [
        "Trying to manipulate or impress people instead of connecting honestly.",
        "Talking only about yourself and not listening.",
        "Ignoring boundaries or pushing after a clear no.",
        "Copying someone else's personality instead of your own.",
        "Expecting instant results from one conversation.",
        "Withdrawing completely after one rejection.",
    ],
}


def _ascii(s):
    repl = {"\u2014": "-", "\u2013": "-", "\u2019": "'", "\u201c": '"',
            "\u201d": '"', "\u2022": "-", "\u00d7": "x", "\u2026": "..."}
    for k, v in repl.items():
        s = s.replace(k, v)
    return s.encode("ascii", "replace").decode("ascii")


def _esc(s):
    return _ascii(s).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def guide_sections(topic):
    """Return (title, subtitle, [(heading, [lines])]) for a topic dict."""
    _slug, title, category, focus, desc, practices = topic
    chapters = CHAPTERS[category]
    sections = []
    sections.append(("Introduction", [
        desc,
        "This guide is general information only. It is not medical, psychological, "
        "or professional advice. If you have a health condition, are pregnant, "
        "take medication, or have concerns, talk to a qualified professional "
        "before changing your diet, training, or habits.",
        "You will get the most from this guide by picking one small action "
        "from each chapter and doing it for a week, rather than trying to do "
        "everything at once. Progress in " + focus + " comes from steady, "
        "repeatable steps.",
        "How to use this guide: read it once through, then use the starter "
        "routine at the end as your daily checklist for the first two weeks.",
    ]))
    for i, (heading, bullets) in enumerate(chapters):
        lines = []
        lines.append("Focus: " + focus + ". This chapter gives you practical "
                     "steps you can start today, not theory alone.")
        for b in bullets:
            lines.append("- " + b.format(focus=focus, title=title))
        # Add two topic-specific practices, rotated per chapter, so each
        # guide's chapters carry its own concrete actions.
        p1 = practices[i % len(practices)]
        p2 = practices[(i + 2) % len(practices)]
        lines.append("- Try this for " + title.lower() + ": " + p1.lower() + ".")
        lines.append("- Also practise: " + p2.lower() + ".")
        sections.append((heading, lines))
    routine = []
    days = ["Day 1", "Day 2", "Day 3", "Day 4", "Day 5", "Day 6", "Day 7"]
    for d, p in zip(days, practices + practices[:3]):
        routine.append(d + ": " + p + ".")
    routine.append("Each evening, tick off what you did and note one thing to improve tomorrow.")
    routine.append("After 7 days, keep the 3 actions that helped most and repeat them for 3 more weeks.")
    sections.append(("Your 7-Day Starter Routine", routine))
    sections.append(("Common Mistakes to Avoid", ["- " + m for m in MISTAKES[category]]))
    sections.append(("Keep Going", [
        "Review this guide after 2 weeks and pick your next focus area.",
        "Track one simple measure weekly: how often you did the routine, and how you felt.",
        "If something is not working, change one thing at a time and give it a week.",
        "Share what helped with a friend; teaching it helps you keep it.",
        "You do not need to be perfect. Steady, kind, consistent effort wins.",
    ]))
    return title, category + " - A Practical Guide", sections


def build_guide_pdf(topic):
    """Build a multi-page PDF (bytes) for one topic, stdlib only."""
    title, subtitle, sections = guide_sections(topic)
    # Pages: list of (kind, text) where kind is title/heading/body/bullet
    pages = []
    cur = []
    cur.append(("title", title))
    cur.append(("subtitle", subtitle))
    cur.append(("body", "By " + SELLER))
    cur.append(("body", "General information only. Not medical advice. "
                       "Consult a qualified professional before changing "
                       "diet, training, or health habits."))
    cur.append(("body", "Contents: Introduction, 5 chapters, a 7-day starter "
                       "routine, common mistakes to avoid, and a closing plan."))
    for heading, lines in sections:
        cur.append(("heading", heading))
        for line in lines:
            if line.startswith("- "):
                cur.append(("bullet", line[2:]))
            else:
                cur.append(("body", line))
    # Paginate: ~44 body lines per page at 10pt, headings take more room.
    all_pages = []
    page = []
    cost = 0
    for kind, text in cur:
        c = 4 if kind == "title" else (3 if kind == "heading" else 1)
        # Wrapped line count, roughly, for pagination.
        wrapped = len(textwrap.wrap(text, 92)) if kind in ("body", "bullet") else 1
        if cost + c + wrapped > 46 and page:
            all_pages.append(page)
            page = []
            cost = 0
        page.append((kind, text))
        cost += c + wrapped
    if page:
        all_pages.append(page)

    def stream_for(page_items):
        out = []
        y = 750
        for kind, text in page_items:
            if kind == "title":
                out.append("BT /F2 20 Tf 50 %d Td (%s) Tj ET" % (y, _esc(text)))
                y -= 34
            elif kind == "subtitle":
                out.append("BT /F1 12 Tf 50 %d Td (%s) Tj ET" % (y, _esc(text)))
                y -= 24
            elif kind == "heading":
                out.append("BT /F2 13 Tf 50 %d Td (%s) Tj ET" % (y, _esc(text)))
                y -= 22
            else:
                prefix = "- " if kind == "bullet" else ""
                wrapped = textwrap.wrap(text, 92) or [""]
                for j, wline in enumerate(wrapped):
                    t = (prefix + wline) if j == 0 else ("  " + wline)
                    out.append("BT /F1 10 Tf 50 %d Td (%s) Tj ET" % (y, _esc(t)))
                    y -= 15
                y -= 3
        return "\n".join(out)

    # Object numbering: 1 Catalog, 2 Pages, then per page: Page, Contents,
    # then fonts F1=Helvetica, F2=Helvetica-Bold.
    n_pages = len(all_pages)
    kids = []
    objs = []
    objs.append("<< /Type /Catalog /Pages 2 0 R >>")
    page_obj_ids = []
    obj_no = 3
    for _ in all_pages:
        page_obj_ids.append(obj_no)
        obj_no += 2
    kids = " ".join("%d 0 R" % i for i in page_obj_ids)
    objs.append("<< /Type /Pages /Kids [%s] /Count %d >>" % (kids, n_pages))
    streams = [stream_for(p) for p in all_pages]
    for pid, stream in zip(page_obj_ids, streams):
        objs.append("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                    "/Resources << /Font << /F1 %d 0 R /F2 %d 0 R >> >> "
                    "/Contents %d 0 R >>" % (obj_no + 1, obj_no + 2, pid + 1))
        objs.append("<< /Length %d >>\nstream\n%s\nendstream" % (len(stream), stream))
    f1 = obj_no + 1
    f2 = obj_no + 2
    # Rebuild with correct font object numbers: page objects above already
    # used obj_no+1/obj_no+2, which are exactly f1/f2, so just append fonts.
    objs.append("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    objs.append("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")
    out, offsets = b"%PDF-1.4\n", []
    for i, o in enumerate(objs, 1):
        offsets.append(len(out))
        out += ("%d 0 obj\n%s\nendobj\n" % (i, o)).encode("ascii", "replace")
    xref = len(out)
    out += ("xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)).encode()
    for off in offsets:
        out += ("%010d 00000 n \n" % off).encode()
    out += ("trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF"
            % (len(objs) + 1, xref)).encode()
    return out


def guide_filename(slug):
    return "guide-%s.pdf" % slug


def ensure_guide_file(topic, directory):
    """Write a guide PDF into directory if missing; return its path."""
    fname = guide_filename(topic[0])
    path = os.path.join(directory, fname)
    if not os.path.exists(path):
        with open(path, "wb") as f:
            f.write(build_guide_pdf(topic))
    return path


def ensure_all_guides(directory):
    """Write every guide PDF that is missing; return (count, total_bytes)."""
    total = 0
    for topic in TOPICS:
        p = ensure_guide_file(topic, directory)
        total += os.path.getsize(p)
    return len(TOPICS), total
