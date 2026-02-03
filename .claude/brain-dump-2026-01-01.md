## 2026-01-01 - Lessons Learned

**Lesson 7: Don't Create Useless "Streaming" (Dec 2025)**
- Created a "streaming" spec that only set a static progress message
- Users still stared at "Creating outfit 1 of 3..." for 20 seconds with no updates
- Optimized for "easy to implement" instead of "solves the problem"
- Buried the real solution in "Future Enhancements (out of scope)"
- Key insight: Before handing spec to Cursor, walk through UX second-by-second

**Lesson 8: Always Test Locally BEFORE Commit/Push (Jan 2026)**
- HEIC orientation fix was committed and pushed before local testing
- Wrong fix (manual rotation) caused double-rotation bug in production
- Had to push a second fix after local testing revealed the issue
- Correct workflow: Implement → Test locally with real data → Commit/Push
- TodoWrite should ALWAYS have "Test locally" BEFORE "Commit/Push"
- If you can't test locally, explicitly acknowledge the risk

