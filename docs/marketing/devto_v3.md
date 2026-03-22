---
title: I had no idea my AI-built app had 12 security problems until I pasted one URL
published: false
tags: vibecoding, security, beginners, ai, webdev
---

I'm not a developer. I mean, I use Cursor and Claude to build stuff, but I don't really read the code. If it works, I ship it.

Last week someone on Reddit mentioned that AI-generated code usually has security issues. I thought "probably not mine, it's a simple app." But it bugged me enough to google "how to check if my code is secure."

Most results were tools for real developers. Install this, run that command, configure YAML whatever. I closed all of them.

Then I found this site where you just paste your GitHub URL and it tells you what's wrong: https://vibesafe.onrender.com

I pasted my repo. 30 seconds later:

**Grade C. 12 issues found.**

Stuff like form inputs that screen readers can't see (apparently you can get sued for that?? 4,000+ accessibility lawsuits in 2024 alone), and some security patterns I don't fully understand but the descriptions were clear enough.

The part that actually helped me was at the top of the results — there's a box that says "copy this and paste into your AI." So I copied it, pasted it into Cursor, and Cursor fixed everything. I didn't have to understand what was wrong. I just had to copy and paste.

Scanned again after the fixes. 100/100. Grade A.

I'm not saying everyone needs to do this. But I had no idea my app had problems, and now I can't un-know that. If you built something with AI and you're about to put it in front of real users, maybe just paste the URL and see what comes back. It takes 30 seconds and it's free.

The thing that stuck with me: it uses the same scanning engine that Dropbox and Slack use (Semgrep), and checks for the same stuff that security auditors look at (OWASP Top 10). So it's not some random checker.

Anyway. Back to building.
