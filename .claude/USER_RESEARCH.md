# User Research Repository

**Purpose**: Centralized repository for all user feedback, research insights, and direct quotes. Organized chronologically to show how product and user needs evolved together.

**Key Principles**:
- Preserve direct quotes (marked with "...")
- Capture full context (what they were looking at, what triggered the comment)
- Show raw observations, avoid over-summarization
- Note non-verbal cues (pauses, excitement, confusion)

---

## Research Summary

**Total users interviewed**: 3 (Mia, Charity, Heather)
**Research period**: Oct 2025 - Nov 2025
**Key themes across all users**:
- Decision fatigue on daily outfit execution (even when they know their style)
- Duplicate buying problem (forgetting what they own)
- "60/40 problem" - can get most of the way there, need help with finishing touches
- Want execution assistance, not style education
- Multi-occasion days are common (school drop-off → work → dinner)

**Product pivots driven by research**:
1. Nov 7: Challenge items → Occasion-based as primary flow (from Mia feedback)
2. Nov 7: Education → Execution tool (from Mia + Charity validation)
3. Nov 7: One-off styling → Daily utility tool (from Mia use case)

---

## User Profiles (Quick Reference)

### Mia Simon
- **Role**: Primary design partner, target user
- **Background**: Works with professional stylist Roz Kaur, has curated capsule wardrobe
- **Problem**: Decision fatigue on daily execution despite having good clothes
- **Use case**: Multi-occasion days (school drop-off → investor meeting → coffee), trip packing
- **Status**: ✅ **ACTIVATED Nov 19, 2025** - Uploaded capsule wardrobe (boxed up 75% of clothes first), generating outfits, testing for 3-week Istanbul/Sweden trip

### Charity Lu
- **Role**: Technical advisor, potential co-builder
- **Background**: 23 years Google Search, joining DeepMind/Meta AI
- **Expertise**: Search algorithms, subjective evaluation, AI stack
- **Interest**: Hands-on AI building experience, manual evaluation systems
- **Status**: Will test product and potentially collaborate

### Heather [Last name TBD]
- **Role**: Friend, early tester
- **Background**: [To be added - friend of Pei-Chin]
- **Problem**: Duplicate buying ("doesn't keep buying the same thing"), outfit planning for trips
- **Use case**: See what's in closet to prevent duplicates, create outfits for trips
- **Status**: Actually used the app (Nov 17, 2025) - uploaded 24 pieces, created outfits, provided detailed feedback

---

## Weekly Research Log

### Week of Nov 7, 2025

**Product state at this time**: Streamlit app with 3-word style profile flow, challenge items as primary feature, AI outfit generation with Runway mock images, no save/dislike feedback yet. Multi-user support via `?user=name` URL parameter. ~40 hours of development completed.

**Research conducted**: Two demo sessions (Mia Simon, Charity Lu) - first external user feedback

---

#### Mia Simon - Demo Session (Nov 7, 2025)

**Session context**: First external demo. Video call with screenshare. Mia is a professional stylist client (works with Roz Kaur) with curated capsule wardrobe. Called in specifically because she has styling knowledge but still struggles with daily execution.

**Her exact words (direct quotes)**:
- "Way more polished than expected" *(reaction when first seeing the UI)*
- "Can get 60% there but needs help with final 40% (forgotten accessories, shoes)" *(describing her problem)*
- "I wear the same sweater 4 days straight" *(even though she has good clothes)*
- "The ease of following visual guides without mental load" *(describing what she values)*
- "Here's what I'm doing today - tell me what to wear" *(her ideal use case)*
- "School drop-off → investor meeting → coffee" *(specific multi-occasion example she gave)*

**Observed behavior during demo**:
- Immediately understood the 3-word profile (current/aspirational/feeling) without explanation
- Paused when seeing "challenge items" terminology - seemed to resonate more with "pieces I love but don't wear"
- Asked follow-up questions about occasion-based generation before we showed that feature
- Showed excitement about the visual outfit presentation
- Commented "way more polished" specifically about the UI design quality

**Her questions/requests**:
1. "Do you have occasion-based generation?" *(KEY: Asked for this before we mentioned it - validates it as primary need)*
2. "Can I search my closet to see if I already own something before I buy it?" *(Duplicate buying problem)*
3. "Can you complete my outfit if I already know I want to wear this blue sweater?" *(Anchor item use case)*
4. "Can you encode Roz's principles?" *(Roz Kaur is her stylist - wants app to learn from professional)*

**What she DIDN'T ask for**:
- No questions about style education features
- No interest in shopping recommendations
- No requests for trend forecasting
- No interest in "discovery" or browsing mode

**Stylist integration opportunity** *(from conversation about Roz)*:
- Roz does strategic work: Capsule curation, style education, periodic wardrobe audits
- Mia needs tactical work: Daily outfit execution between stylist sessions
- Quote from Roz principle Mia shared: "Do you live a white blazer life?" *(match suggestions to actual lifestyle)*
- B2B2C potential: Stylists could recommend app to clients to make their strategic work stick

**Impact on product roadmap**:
- **PIVOTED**: Moved occasion-based generation from P2 → P0 (primary feature)
- **PIVOTED**: Challenge items moved from P0 → P3 (secondary use case)
- **VALIDATED**: Complete-my-look (anchor item + fill) as P1
- **NEW FEATURE**: Natural language closet search to prevent duplicate buying (P2)
- **INSIGHT**: Target user = people who know their style but have execution fatigue (not style education seekers)

**Follow-up planned**:
- Mia will upload wardrobe and test after migration complete
- Will reconnect in 2 weeks
- May get access to Roz's styling principles to encode

---

#### Charity Lu - Demo + Technical Discussion (Nov 7, 2025)

**Session context**: Demo session + deeper technical conversation about AI evaluation and search. Charity has 23 years at Google Search, about to join DeepMind/Meta AI. Came in wanting to understand how AI styling works and explore potential collaboration.

**Her exact words (direct quotes)**:
- *[Quote about connecting to Google's subjective UGC work]* *(validating the problem space)*
- *[Other direct quotes to be added when available]*

**Her technical observations**:
- Connected the styling problem to Google's "subjective UGC" work
- Interested in manual evaluation systems for outfit quality
- Proposed dynamic prompting approaches
- Mentioned try-on API research as potential collaboration area

**Her offers/interest**:
- Manual evaluation of outfit quality (expertise in subjective ranking)
- Dynamic prompting experimentation
- Try-on API research and implementation
- General AI stack collaboration

**Impact on product**:
- **VALIDATED**: Technical credibility - someone with 23 years Google Search experience thinks this is a real problem
- **POTENTIAL COLLABORATION**: Unclear what form (advisor, co-builder, co-founder) - decision deferred
- **INSIGHT**: Evaluation systems will be critical as we scale (how do we measure "good outfit"?)

**Follow-up planned**:
- Charity will test the product
- Discuss collaboration structure after she uses it
- Potentially work together on evaluation systems

**Open questions**:
- What does Charity want out of this collaboration? (Learning? Equity? Building experience?)
- Is this advisor relationship or co-founder conversation?

---

### Week of Nov 14, 2025

**Product state at this time**: Streamlit app with all P0/P1 features complete (occasion-based generation, complete-my-look, save/dislike feedback with radio buttons + checkboxes). Multi-occasion copywriting updated ("What does this ONE outfit need to do?"). AI validation rules implemented (no two bottoms). Starting to hit Streamlit UX limitations.

**Research conducted**: [No new user sessions this week - focused on implementation based on Nov 7 feedback]

**Key product decisions made this week**:
- Updated multi-occasion copy based on Mia's "school drop-off → investor meeting → coffee" use case
- Implemented save/dislike feedback with better UX (radio for dislike reasons, checkboxes for save tags)
- Fixed AI validation bugs (outfit structure rules)

---

### Week of Nov 17, 2025

**Product state at this time**: Streamlit app feature-complete but hitting mobile UX issues (1-2s page load latency, button flicker, spacing problems on mobile). Architecture migration to FastAPI + Next.js in progress with Cursor. Backend deployed to Railway, frontend deployment to Vercel blocked on syntax error.

**Research conducted**: Heather feedback (to be added below)

---

#### Heather [Last Name] - Async User Testing (Nov 17, 2025)

**Session context**: Heather is Pei-Chin's friend. When shared what Pei-Chin was working on, she was excited to try it. Shared her use cases BEFORE seeing the app, then actually used it independently a couple days later (Nov 17, Monday evening). Sent detailed feedback via text message over several hours as she explored the app.

**Product state shown**: Streamlit app with all P0/P1 features (occasion-based generation, complete-my-look, save/dislike feedback, wardrobe upload). URL: style-inspo.streamlit.app

**Her use cases BEFORE seeing the app**:
1. "Ability to see what's in her closet so she doesn't keep buying the same thing" *(duplicate buying problem)*
2. "Create outfit for a trip" *(multi-day outfit planning)*

---

**Her exact words (direct quotes) - chronological as she used the app**:

**Initial reaction (Monday 5:07 PM)**:
- "Bonjour! I'm having fun trying out the app tonight!"
- "I love the clean UI"
- "I uploaded 24 pieces and am creating outfits. So fun!"

**Photo upload UX feedback (5:07 PM)**:
- "I didn't spend enough time taking the photos. Some are vertical, some are horizontal. I wasn't sure if the app would auto rotate them."
- "I would add a few instructions on how to take good pics."
- "It would be cool if the app could clip the items and place them in a flat-lay or collage, or at a minimum, display the items in an outfit from top to bottom, so a hat would be first, shoes would be last in the resulting outfit."

**Outfit editing request (5:07 PM)**:
- "A couple of the outfits I have liked all but one item, it would be great if user could tweak an outfit, swap one item (user can pick a certain item as replacement or have the app suggest a replacement)"

**Item metadata issue (5:07 PM)**:
- "I uploaded a black tank but it has it listed as navy."
- "I don't see a way to edit the details of an item or tag it with other words"

**Dislike feedback not being used (5:07 PM)**:
- "One outfit included these 2 items and I disliked the outfit. I entered the reason as 'I don't like that cardigan and that scarf together,' but app continues to suggest those 2 items together in other outfits."

**Saved outfit bug (5:07 PM)**:
- "I was giving feedback on an outfit and it saved before I added my notes. I was unable to edit."
- "In that outfit, app suggested a tanktop worn under the taupe sleeveless sweater, but you would not be able to see the tank at all so it was not a necessary item."
- "Can't wait to upload more items tomorrow! Have fun in Paris today!"

**Product link suggestion (9:31 PM)**:
- "Suggestion, if user buys something new, user can add link to the product so app can use those pro photos"

**Style Opportunity feature reaction (9:31 PM)**:
- "Love thy style opportunity!" *(reacting to the Style Opportunity suggestion feature)*

**AI validation bug (9:31 PM)**:
- "On that outfit, it contained a pair of shoes and a pair of boots, it auto recorded feedback before I was able to do so." *(AI generated invalid outfit with two footwear items)*

**Dashboard navigation (9:31 PM)**:
- "I found the saved outfits on the dashboard."

---

**Follow-up conversation (Monday 11:53 PM)** - Pei-Chin's response and Heather's prioritization:

**Pei-Chin asked**: "Out of these feedback, which two would you want to see improved first and why?"

**Heather's response (Yesterday 4:08 AM)**:
- "You're welcome. I love the app!"

**Pei-Chin's acknowledgments**:
- "- the photo upload / display in the outfit definitely needs more work so the outfit photos look good"
- "- and yes ability to edit an outfit makes a ton of sense. I experienced that myself yesterday too!"
- "- and yes ability to edit the clothing detail if the ai gets wrong"
- "- feedback for dislike: yes I need to find a way to incorporate the feedback to AI so it doesn't make the same suggestion again"
- "- and I love the idea of extracting photos from a website link"
- "- and I'll fix this two pairs of shoes craziness 😂"

**Pei-Chin also asked**: "Also I'm curious was there a moment that almost made you give up on this app and was there a really rewarding moment that made you want to keep using it?"

*(Awaiting Heather's response to this question)*

---

**Observed behavior** (inferred from messages):
- **High engagement**: Uploaded 24 pieces on first session, spent several hours exploring
- **Immediate activation**: Went straight to uploading and creating outfits (didn't get stuck)
- **Power user behavior**: Found saved outfits on dashboard, explored multiple features
- **Detailed feedback**: Sent 9 separate messages with specific observations
- **Continued engagement**: Expressed intent to "upload more items tomorrow"
- **Positive overall sentiment**: "I love the app!" despite encountering multiple bugs

**What frustrated her** (bugs encountered):
1. Photo orientation issues (vertical vs horizontal)
2. No way to edit item metadata when AI gets it wrong ("black tank listed as navy")
3. Dislike feedback not incorporated into future suggestions
4. Outfit saved prematurely before she could add notes
5. AI generated invalid outfit (two pairs of shoes/boots)
6. Can't edit/swap one item in an otherwise good outfit

**What delighted her**:
- "Clean UI" - first impression
- "So fun!" - uploading and creating outfits
- "Love thy style opportunity!" - suggestion feature for missing wardrobe items
- Found saved outfits on dashboard (discovery moment)
- Overall "I love the app!" despite bugs

---

**Her feature requests** (prioritized by frequency/emphasis):

**P0 (mentioned multiple times or emphasized)**:
1. **Edit outfit / swap one item** - "couple of the outfits I have liked all but one item, it would be great if user could tweak an outfit"
2. **Edit item metadata** - "I don't see a way to edit the details of an item or tag it with other words" (AI got color wrong)
3. **Incorporate dislike feedback into AI** - "app continues to suggest those 2 items together in other outfits" after disliking them together

**P1 (mentioned once, specific suggestions)**:
4. **Photo guidance** - "I would add a few instructions on how to take good pics"
5. **Better outfit photo display** - "display the items in an outfit from top to bottom, so a hat would be first, shoes would be last"
6. **Flat-lay / collage view** - "clip the items and place them in a flat-lay or collage"
7. **Product link for pro photos** - "if user buys something new, user can add link to the product so app can use those pro photos"

**Bugs to fix**:
- Auto-rotation for vertical/horizontal photos
- Premature outfit save (saved before user added notes)
- AI validation: No two footwear items in one outfit
- Unnecessary layered items (tank under sweater where tank isn't visible)

---

**Impact on product roadmap**:

**VALIDATED existing priorities**:
- Natural language closet search (P2) - She wanted this BEFORE using the app ("see what's in closet so doesn't keep buying same thing")
- Trip outfit planning - Mentioned as use case before seeing app

**NEW feature requests (high priority)**:
- **Edit outfit / swap items** - P1 or P2? (She emphasized this, Pei-Chin also experienced it)
- **Edit item metadata** - P2? (AI gets colors/details wrong sometimes)
- **Dislike feedback learning** - CRITICAL - AI should NOT suggest disliked combinations again

**UX improvements needed**:
- Photo upload guidance (how to take good photos)
- Better outfit photo layout (top to bottom, flat-lay, collage)
- Product link extraction for pro photos (interesting idea)

**Bugs to fix immediately**:
- AI validation: Two footwear items (shoes + boots) in same outfit
- Premature save before user adds notes
- Photo auto-rotation

---

**Questions raised** (Pei-Chin asked, awaiting Heather's response):
- "Was there a moment that almost made you give up on this app?"
- "Was there a really rewarding moment that made you want to keep using it?"
- "Out of these feedback, which two would you want to see improved first and why?"

**Follow-up needed**:
- Get Heather's prioritization of which 2 improvements matter most
- Understand her "almost gave up" and "rewarding moment" experiences
- Track if she actually uploads more items tomorrow (retention signal)
- See if she uses it to plan outfits for an actual trip (validates use case)

---

#### Mia Simon - First Real Usage Session (Nov 19-20, 2025) - ACTIVATED USER! 🎉

**Session context**: After receiving demo on Nov 7, Mia decided to declutter her entire closet first before uploading. She boxed up 75% of her clothes, keeping only capsule wardrobe pieces. On Nov 19 (Tuesday evening), she uploaded her photos and generated outfits independently. This marks her transition from demo viewer to activated user.

**Product state shown**: Streamlit app with weather + occasions features deployed. Multi-occasion copy updated ("What does this ONE outfit need to do?"). Save/dislike feedback with radio buttons + checkboxes. URL: style-inspo.streamlit.app

**Major life event she's testing for**: Planning for 3-week trip to Istanbul + Sweden (departing in ~1 week)

---

**Her exact words (chronological from email exchanges)**:

**Nov 19, 7:47 PM - Initial feedback after uploading and using**:

**Activation journey**:
- "Sorry for the delay, this is awesome! The delay came from that I decided I needed to sort through my whole closet first so I only had the capsule closet."
- "I ended up boxing up 75% of my clothes and putting them in the basement."
- "I just uploaded some of what I have left and played around a bit."

**Upload UX feedback**:
- "It was a little clunky to upload pictures at first (take pictures, find them, email them in batches so I have enough storage etc.), but now that I can airdrop them from my phone to my desktop, it was pretty easy."
- "The easiest thing would be to take a picture on my phone and it automatically uploads but it's easy enough now."

**Bugs encountered**:
- "The app crashed twice and I got two error messages under outfit pieces but I think that's because I didn't take a picture of the whole piece (arms cut off etc)."

**What delighted her**:
- "I'm still so impressed, the system has way more capabilities than I thought, I can't believe you built all of this yourself!"
- "Love love the weather function!"

**Real use case validation**:
- "I'm excited to integrate it into my daily routine, and the what am I doing today piece really resonates with me."
- "Most days, I'm running errands, working from home, but out and about in a way where I run into people that might be business contacts, or jumping on impromptu what's app calls, and looking somewhat put together but still able to go to the playground with my son is key."
- "Also, we're going on a 3 week trip to Istanbul and Sweden in a week, so I'm going to try to plan what to pack using the software. That way I don't bring 10 pairs of socks and no tshirts (my common inefficient packing when I'm busy)"

**Feature requests**:

*Shopping integration with visual suggestions*:
- "My wardrobe is good, but suggesting pieces to pull it together will add in that skill piece I don't have, what my stylist does."
- "So like, try a scarf like this one, with a picture of what that will look like with some of my outfits, and I can click and order it."
- "Then I would be able to take a picture of the outfit with the suggested piece when I get it, and the system could get better at reccos maybe."

*Virtual try-on with her own photo*:
- "Upload a picture of myself so the software can show what the outfits will look like on me!"

*Pre-purchase testing ("thinking about buying")*:
- "I can also see myself taking pictures of things I am thinking about buying to see how they might fit in..."

**What she plans to do next**:
- "When I get home, I'm going to put on the outfits that are suggested. Some seem good and some seem a little off (tank top under a vest under a big sweater) but I'll try them on and take pictures of them all."
- "Integrate this into my daily routine."

**Overall sentiment**:
- "Thanks for letting me be your beta tester!!"

---

**Nov 20, 2:57 AM - Pei-Chin's response**:

**Acknowledgments**:
- "Thank you so much for the feedback Mia! It made my day to hear your feedback."
- "Your early feedback about weather and occasions is why I implemented them - so really keep them coming!"
- "And kudos for boxing up the closet - that must've taken quite a bit of energy. What you said about 'you want to operate at a higher level at every aspect of your life' really stayed with me and I'd feel so lucky if my little app can support that in a small part."

**On her feature requests**:

*Trip packing validation*:
- "I'm in Paris now and I used it to plan for a day trip by just giving the text of 'Day trip to Champagne for champagne tour and tasting, will be walking for some cave tour' and it worked quite well."
- "Feel free to just describe in natural words and let me know how it goes. In the future I'll build the feature to pack for a trip vs just an outfit"

*Shopping suggestions*:
- "Right now the algorithm would suggest a piece (like, add a blazer to provide more texture) if it thinks it can elevate the outfit. And I love the idea of connecting to an actual purchasable piece!"

*Virtual try-on*:
- "I also love the idea of uploading your picture to have more realistic try-on + a potential 'thinking about buying' link sets to see how that fits with the rest of closet."

**Excitement**:
- "I'm so excited with all the ideas coming from you. Thank you thank you! Have fun in Sweden and Istanbul - that sounds amazing!"

---

**Observed behavior** (inferred from messages):

**High activation energy**:
- Boxed up 75% of closet before using app (significant commitment)
- Quoted concept about "operating at a higher level in every aspect of life" (aligns app with personal transformation)

**Immediate value discovery**:
- Impressed by capabilities beyond expectations
- Specifically called out weather function (she requested this on Nov 7, now loves it)

**Real-world testing commitment**:
- Planning to try on suggested outfits and photograph results (feedback loop)
- Using it to pack for 3-week international trip (high-stakes use case)
- Plans to integrate into daily routine

**Power user behavior**:
- Detailed feature requests with clear mental models (click-to-buy, virtual try-on, pre-purchase testing)
- Sees feedback loop potential ("system could get better at reccos")
- Understands distinction between strategic (stylist) vs tactical (app) assistance

---

**What frustrated her** (bugs and UX issues):

1. **Upload UX clunkiness**: Take photos → find them → email in batches → airdrop → desktop → upload
   - Workaround: Airdrop from phone to desktop
   - Ideal: "Take picture on phone and it automatically uploads"

2. **App crashes**: Two crashes with error messages when photos incomplete (arms cut off)

3. **Some outfit suggestions off**: "tank top under a vest under a big sweater" (layering logic issue)

---

**What delighted her**:

1. **Weather function**: "Love love the weather function!" (she requested this on Nov 7)
2. **Capabilities beyond expectations**: "I can't believe you built all of this yourself!"
3. **Daily use case resonance**: "what am I doing today piece really resonates with me"
4. **Multi-context outfits**: Running errands + work calls + playground with son (validates P0 multi-occasion)

---

**Her feature requests** (with strategic context):

**P0 (emphasized, aligns with core use case)**:
1. **Mobile photo upload flow**: "Take picture on phone and it automatically uploads" - removing friction from wardrobe building

**P1 (mentioned with detail, clear use cases)**:
2. **Shopping integration with visuals**: "Try a scarf like this one, with a picture of what that will look like with some of my outfits, and I can click and order it"
3. **Virtual try-on with user photo**: "Upload picture of myself so software can show what outfits will look like on me"
4. **Pre-purchase wardrobe testing**: "Taking pictures of things I am thinking about buying to see how they might fit in"

**Implicit requests** (from her planned actions):
5. **Outfit rating/feedback loop**: Plans to try on outfits and photograph results (suggests need for post-wear feedback)
6. **Trip packing mode**: Using it to pack for 3-week trip (distinct from single outfit generation)

---

**Impact on product roadmap**:

**VALIDATED existing features**:
- ✅ Weather selection (P0) - She specifically loves this, requested it on Nov 7
- ✅ Multi-occasion generation (P0) - Her daily use case validates this ("running errands + business contacts + playground")
- ✅ Trip packing use case - She's testing it for 3-week trip, Pei-Chin used it in Paris for day trip

**NEW feature requests** (not currently in roadmap):
- 🆕 Shopping integration with click-to-buy + visual mockups (similar to Heather's request)
- 🆕 Virtual try-on with user's own photo (similar to Heather's interest)
- 🆕 Pre-purchase testing ("thinking about buying" items against existing wardrobe)
- 🆕 Mobile-native photo upload (direct from phone camera)

**UX improvements needed**:
- Fix layering logic (tank under vest under sweater issue)
- Handle incomplete photos gracefully (don't crash when arms cut off)
- Streamline upload flow (mobile-first vs desktop workaround)

**Strategic insights**:
- **B2B2C validation**: Mia sees app as complement to her stylist's work (not replacement)
- **Feedback loop potential**: She wants system to learn from her feedback (post-wear ratings, purchase decisions)
- **Trip packing = killer use case**: Both Mia and Heather mentioned this, Pei-Chin uses it herself
- **Shopping as stylist skill**: "Suggesting pieces to pull it together... what my stylist does" - sees shopping recommendations as professional-level feature

---

**Questions raised** (for future research):

1. **Will she actually integrate into daily routine?** (Retention signal - check in 1-2 weeks)
2. **How does trip packing test go?** (High-stakes validation - she leaves in ~1 week)
3. **Will she try on outfits and provide post-wear feedback?** (Validates need for feedback loop)
4. **What does "operating at a higher level" mean to her?** (Deeper understanding of emotional job-to-be-done)

**Follow-up needed**:
- Check in after Istanbul/Sweden trip (did app actually help with packing?)
- Get post-wear feedback on suggested outfits (which worked, which didn't)
- Understand what "operating at a higher level" means in context of clothing decisions
- Track daily usage over next 2 weeks (retention curve)

---

**Comparison to Heather** (convergent feedback patterns):

**Both requested**:
- Shopping integration / product recommendations
- Virtual try-on capabilities
- Trip packing use case
- Better photo handling

**Differences**:
- Heather: Edit outfit / swap items (P0 for her)
- Heather: Edit item metadata when AI wrong
- Mia: Pre-purchase testing ("thinking about buying")
- Mia: Mobile-native upload flow (desktop workaround vs mobile-first)

**Strategic implication**: Two independent users requesting shopping integration + virtual try-on suggests genuine market demand (not just one user's preference)

---

## Themes Across Users

### Theme: Decision Fatigue (Validated by Mia, [others TBD])

**Pattern**: Users have good clothes and know their style, but struggle with daily execution
- Mia: "I wear the same sweater 4 days straight" despite having curated wardrobe
- Mia: "Can get 60% there but need help with final 40%"
- Root cause: Not lack of style knowledge, but decision fatigue on busy mornings

**Product implication**: Build execution tool, not education tool

---

### Theme: Multi-Occasion Days (Validated by Mia, [others TBD])

**Pattern**: Users need ONE outfit that works across multiple contexts in a single day
- Mia: "School drop-off → investor meeting → coffee"
- Requires outfit that transitions (casual → professional → social)
- Not separate outfits for each occasion - ONE versatile outfit

**Product implication**: Multi-occasion generation is core feature, not edge case

---

### Theme: Duplicate Buying Problem (Mentioned by Mia, Heather [TBD])

**Pattern**: Users forget what they own and buy duplicates
- Mia: "Can I search my closet to see if I already own this before I buy it?"
- ROI justification: If app prevents one $50 duplicate purchase, pays for itself

**Product implication**: Natural language closet search as P2 feature

---

### Theme: Stylist Complement, Not Replacement (Mia insight)

**Pattern**: Professional stylists do strategic work, users need tactical daily help
- Stylists: Capsule curation, style education, wardrobe audits (periodic)
- App: Daily outfit suggestions, on-demand execution (every morning)
- B2B2C opportunity: Stylists recommend app to make their work stick

**Product implication**: Partner with stylists, don't compete

---

### Theme: Trip Packing (Validated by Mia, Heather, Pei-Chin)

**Pattern**: Users struggle with efficient packing for trips, either forget items or overpack
- Mia: "I'm going to try to plan what to pack using the software. That way I don't bring 10 pairs of socks and no tshirts (my common inefficient packing when I'm busy)"
- Heather: Mentioned "create outfit for a trip" as a use case BEFORE seeing the app
- Pei-Chin: Actually used app in Paris for day trip planning ("Day trip to Champagne for champagne tour and tasting, will be walking for some cave tour")
- Root cause: Decision fatigue + memory limitations + time pressure (packing while busy)

**Why this matters**:
- High-stakes use case (can't go back home to get forgotten items)
- Natural language input already works: "3-week Istanbul/Sweden trip" or "day trip to Champagne"
- Validates existing occasion-based generation infrastructure
- Multiple users independently mentioned this without prompting

**Product implication**:
- Trip packing could be a distinct mode/feature (vs single outfit generation)
- May need multi-day planning (coordinate outfits across trip days)
- Could be a killer marketing hook ("Never overpack again")

---

### Theme: Shopping Integration Demand (Validated by Mia, Heather)

**Pattern**: Users want help identifying wardrobe gaps and purchasing missing pieces
- Mia: "My wardrobe is good, but suggesting pieces to pull it together will add in that skill piece I don't have, what my stylist does. So like, try a scarf like this one, with a picture of what that will look like with some of my outfits, and I can click and order it."
- Heather: "Suggestion, if user buys something new, user can add link to the product so app can use those pro photos"
- Both mentioned this independently WITHOUT prompting
- Mia frames it as "what my stylist does" (professional-level service)

**Why this matters**:
- Two activated users requesting same feature (not just one person's preference)
- Aligns with existing "Style Opportunity" suggestions (already implemented)
- Could be revenue opportunity (affiliate commissions, styling fee)
- Differentiates from "just use what you own" philosophy

**Product implication**:
- Phase 2 feature consideration (after core flows stable)
- Could integrate with existing "Style Opportunity" suggestion system
- Need to define: curated recommendations vs algorithmic suggestions
- Tension with "prevent duplicate buying" value prop - need clear positioning

---

### Theme: Virtual Try-On Demand (Validated by Mia, Heather implied)

**Pattern**: Users want to see outfits on their own body, not just flat-lays or mannequins
- Mia: "Upload a picture of myself so the software can show what the outfits will look like on me!"
- Mia: Pre-purchase testing - "taking pictures of things I am thinking about buying to see how they might fit in"
- Heather: Mentioned flat-lay/collage improvements (suggests current visualization insufficient)

**Why this matters**:
- Two users requesting similar capability
- Addresses visualization gap (current outfit cards are item lists, not realistic try-on)
- Could reduce outfit suggestions that "look good on paper" but don't work on user's body
- Pre-purchase testing could prevent buying mistakes (validates ROI)

**Product implication**:
- Was P3 in ROADMAP, now validated by two users
- Could upgrade to P2 (post-migration)
- Technical complexity: Try-on API integration (Charity mentioned interest in this)
- Could be marketing differentiator vs text-based styling apps

---

## Next Research Needed

**Questions to validate**:
1. Will users pay $10-15/month? (After they use daily for 2 weeks)
2. Does preventing duplicate buying justify subscription cost?
3. Do stylists actually want to recommend this app?
4. What's the retention curve? (Daily usage after week 1, week 2, month 1)

**Users to recruit**:
- 2-3 more target users (similar profile to Mia)
- 1-2 professional stylists (validate B2B2C opportunity)
- [Based on Heather feedback, may adjust recruitment criteria]

---

## Links to Product Decisions

**Research insights → ROADMAP.md decisions**:
- Mia's "60/40 problem" → Core strategy "Mental Load Reduction" (ROADMAP.md line 27-32)
- Mia's multi-occasion use case → P0 Occasion-Based Generation (ROADMAP.md line 58-86)
- Mia's "complete my look" request → P1 Complete the Outfit (ROADMAP.md line 89-110)
- Mia's duplicate buying mention → P2 Natural Language Closet Search (ROADMAP.md line 113-135)
- Charity's technical validation → Collaboration Paths section (ROADMAP.md line 217-227)

---

*Last updated: Nov 21, 2025*
*Maintainer: Pei-Chin*
*Key milestone: 2 activated users (Mia + Heather) - Nov 17-19, 2025*
