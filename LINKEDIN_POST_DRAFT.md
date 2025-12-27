# LinkedIn Post Draft - December 2025

**Status:** Draft for editing


Reflections in the past month on my solo building journey...

=== Progress that energizes ===

I have users other than me now! One user has entrusted 100+ pieces of clothing in my little app <3  And I loved learning about why a user wants to use the app to begin with, because it's rarely just about the tech. A moment I really cherished is whenAnd I got the joy of talking to users and hearing their emotional journey about this product. For exapmle, one user whants elevate every aspect of their life and wearing the outfit that best suits her energy and the needs of her day is part of it. it just reminded me the why - if my little app can help create a better day one outfit at a time, I feel that's the impact it does in its small part. And getting real user feedback / ideas is the best. Some of the best ideas like - let me see this thing I'm thinking about buying fits with the rest of my closet. I can't stop using it now!

The app graduated from prototype to real infrastructure—Next.js, S3, proper deployment, logging. It feels like leveling up from toy project to actual product. What a time to be alive to be able to build this on my own no matter where I am.  

=== The quality problem ===

While I'm proud of building this app but I'm not happy about the quality of the outfit. 70% of the outfits are.. fine. like the AI was generating outfits that were... fine. "Yeah, that looks fine but I could've created that myself"  maybe 20% of them are 'wow I can't wait to put this on' and then 10% are just straightout nonsense. And I want more of the wows.

Since eval is all the rage of in AI product development I want to learn how to do that. So Claude Code and I built an eval system. Rated 100+ AI-generated outfits across different models and prompts. The eval fatigue is real—at one point I felt genuinely lost in the data and pasted everything into Claude Opus asking for help.

Here's what I learned: **LLMs default to safe.**

They're trained on billions of examples, so they learn the center of mass. 4-star outputs are the statistical norm. 5-stars live in the creative tail of the distribution. And RLHF makes it worse—models learn that the penalty for bad outputs > reward for exceptional ones, so they play it safe.

**Lack of suckiness doesn't make a product great.**

I realized I needed to chase 5-star moments before worrying about fixing embarrassing 1-2 star failures. Get to greatness first, then eliminate the misses.

Now I'm rewriting prompts to explicitly push toward creative risk. Teaching the AI that 5-star outfits can break rules if they know why.

=== Workflow evolution ===

My workflow keeps changing as new tools emerge:

**What's working:** Claude Code generates detailed specs, I feed them to Cursor. This works way better than me casually prompting Cursor directly—the AI writes more thorough specs than I'd bother to type.

**Also cool:** Claude Code web. Being able to write code while I'm out and about? Game-changing for a one-person show.

**Still a pain point:** Test execution. Antigravity is impressively autonomous, but *too* aggressive—it'll build whole new features to solve an issue without checking with me first. I don't feel like I can trust it yet.

I don't know if this is how everyone will build products in 2025, but it's how I'm building mine right now. Constantly adapting the workflow, feeling the gaps, building tools to understand what "meh" means, then fixing it.

The app graduated from prototype to real product. Now the product needs to graduate from competent to compelling.

---

## Notes
- Voice: conversational, thinking out loud, vulnerable about uncertainties
- Structure: === headers like October post
- Concrete: specific tools, numbers, actual experiences
- Ends as learner, not expert
