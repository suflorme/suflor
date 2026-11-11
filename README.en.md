<p align="center">
  <a href="README.md">Türkçe</a> · <b>English</b>
</p>

<p align="center">
  <img src="gorsel/en/hero.png" alt="Suflor.me: the assistant's cards in the corner of a meeting; an enlarged Note card: 12% was said in the meeting; the source shows 8% over the last 7 days." width="100%">
</p>

<p align="center">
  <b>A voice assistant for your meetings.</b> It runs on your Mac, knows your project and whispers the right line at the right moment.
</p>

<p align="center">
  <img alt="macOS 14+" src="https://img.shields.io/badge/macOS-14%2B-175E46?style=flat-square">
  <img alt="Apple Silicon" src="https://img.shields.io/badge/Apple%20Silicon-M%20series-175E46?style=flat-square">
  <img alt="Status: beta" src="https://img.shields.io/badge/status-beta-C9973A?style=flat-square">
  <img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-6B6F68?style=flat-square">
</p>

<p align="center">
  <a href="#installation">Installation</a> ·
  <a href="#live-data-on-a-card-as-the-meeting-unfolds">Live data cards</a> ·
  <a href="#it-joins-the-meeting-by-voice">Joins the meeting</a> ·
  <a href="#privacy">Privacy</a> ·
  <a href="KILAVUZ.md">Guide (Turkish)</a>
</p>

---

In theatre, the prompter (*suflör* in Turkish) whispers the line an actor has forgotten from the wings. Suflor.me does the same in
your meetings. You focus on the conversation. It listens, remembers your project's history and, when it matters, says one sentence.

<p align="center"><img src="gorsel/en/ozellikler.png" alt="Highlights: speaks in the meeting, answers participants, runs the meeting, live translation, whispers to you, remembers history, hands-free, private meeting" width="100%"></p>

## Live data on a card, as the meeting unfolds

This is the heart of Suflor.me: as the conversation moves, it **finds the information that fits the topic and puts it on a card with its source.** When someone
asks for a number, a date or an earlier decision, the answer reaches you without interrupting the meeting; when a figure said aloud doesn't match the record, it warns you.

<p align="center"><img src="gorsel/en/canli-veri.png" alt="In the meeting Ayla says conversion reached 12 percent; cards: Answer (source: product metrics, 8 percent this week), Note (conflict alert), Say (backup plan question)" width="100%"></p>

- **Answers with a source:** when you ask *"What was that number last week?"* the card gives the figure, the period and the source. A source can be past meetings,
  project documents (indexed on this Mac) or a live data source you have turned on.
- **Conflict alert:** if a figure, date or responsibility mentioned in the meeting disagrees with an earlier record or with live data, a note puts the two side by side:
  *"12% was said in the meeting; the source shows 8% over the last 7 days."* You make the correction; the assistant never says it aloud.
- **Live data source (optional):** turn on a connector that serves product or campaign metrics in Settings, and the current value is queried when the topic comes up.
  Only a read query goes to the source (metric, period, channel); no names and no transcript quotes. At most one card per topic every ten minutes.
- **When you get stuck:** Option + Shift + O (*What should I say?*) suggests a single sentence that fits the moment.
- **Outside companies and people:** when a new customer, competitor or person comes up, a short card from open sources appears; a single-source fact is marked "unverified".
  Only the name and topic go into the search; it is off in a private meeting.

## It joins the meeting by voice

Suflor.me is not just a note taker. If you want, your assistant joins the meeting: you call it by name and everyone hears the answer.
Once you've called it, the other participants can ask it questions too. You can even hand the whole meeting over to it.

<p align="center"><img src="gorsel/en/toplantida.png" alt="A moment from a meeting: Deniz hands the meeting to Defne; Defne opens the agenda, answers Ayla's question from last week's meeting and invites Can, who has been quiet" width="100%"></p>

- **Speaks in the meeting:** *"Defne, which tasks are left this week?"* The answer is read aloud for everyone. The assistant never
  interrupts; it waits its turn and stops if someone starts speaking. *"Defne, stop"* or Option + Shift + S silences it at once.
  Turn it on in Settings → Assistants speak in meetings; in a web meeting its voice is mixed into your microphone only while it speaks.
- **Answers participants' questions:** once you've called it, anyone in the meeting can ask *"Defne, …"*. When you want an answer
  only for yourself, use the Talk button on the panel.
- **Runs the meeting:** *"Defne, you run the meeting. Agenda: sign-up page, support and pricing."* It takes the agenda from that
  sentence or from the calendar event. It opens each item, invites quiet people in, gently wraps up long monologues and revives a long
  silence. When time is up it summarises and asks for a decision; at the close it reads out decisions and owners. You can step in at
  any time with *"next item"*, *"more time"*, *"summarize"*, *"hold on"*, *"carry on"* or
  *"I'll take it from here"*.
- **Private meeting:** one tap and Suflor.me hears, writes and processes nothing; the assistant stays silent.

### Two assistants: inside and outside

You can have two assistants. One looks after your tasks and project (inside); the other briefs you on outside companies and people in the meeting (outside; default name Roxie).
Each answers to its own name and speaks in its own voice.

<p align="center"><img src="gorsel/en/asistanlar.png" alt="Ayla asks Defne for last week's date and Defne answers; Kerem from the other company asks Roxie about a firm and Roxie gives a single-source fact marked unverified; a repeated question gets one answer" width="100%"></p>

- **The other side can ask too:** once you have called the assistant, everyone in the meeting can ask it by name.
- **One answer per question:** if the same question comes in again right away, it isn't answered twice.
- **It reads the screen too:** when the other side shares a screen, the text on it is added to the assistant's context in batches; you are warned if a password shows.

## It removes the language barrier

- **Live translation:** the other side's words in another language appear translated on the panel, right under each line. In a
  continuous conversation a translation arrives in about a second.
- **Spoken translation:** with headphones on, a short gist of the translation (eight words at most) is read into your ear; the full
  translation stays on the panel. In a browser meeting the other side's audio is lowered meanwhile.
- **Answers in your language:** ask the assistant in English and it answers in English.

## It whispers to you

The assistant follows the meeting and sends four kinds of cards. With the Mac app running they appear as separate boxes at the bottom centre of the screen, over the meeting video; click one to open it, and they are not visible when you share your screen. Without the app they appear in a small strip in the corner of the meeting screen and
on the panel. Three small buttons next to each card: done, later, not needed.

<p align="center"><img src="gorsel/en/kartlar.png" alt="Four card types: Say, Stop, Answer, Note" width="100%"></p>

- **Measured:** it speaks more or less depending on your role in the meeting (chair, participant, listener). Unprompted Say and Note
  cards interrupt at most once a minute. **Quiet** sends no cards for 10 minutes.
- **Really whispers (optional):** with headphones on, a Stop card is read into your ear in a short voice; no need to look at the screen.
- **What do I say?:** when you're stuck, one tap (Option + Shift + O) suggests a one-sentence line for the moment.
- **Evidence:** press Option + Shift + K (or say *"kanıt al"*, the Turkish voice command) to save a picture of the meeting screen. While the other
  side is sharing their screen, a picture is saved automatically every time the screen changes. It warns you if a password is visible.
- **Tells you when your name comes up:** when the other side says your name, or when you've been talking for more than ninety
  seconds, the panel shows it right away.

### Three moments of a meeting

| Before | During | After |
|---|---|---|
| **Start** from the calendar. The agenda is set; the project summary, people and open tasks are ready. | Live transcript, cards, translation; if you want, the assistant speaks or runs the meeting. | Summary and meeting output: decisions, tasks with owners and dates, open questions. A mind map by agenda item. PDF or email draft. A closing round lets you settle tasks and decisions in minutes. |

## After the meeting: tasks and decisions

When the meeting ends, the assistant doesn't make you read out every decision and task; it opens a **closing round**: you go through each task with *Done*, *Postpone* or *Later*, and each decision with *Approve*.
What you handled collects in the **Decisions and tasks** panel: tasks with an owner and a date, decisions still open, and tasks assigned to you, all in one place.

<p align="center"><img src="gorsel/en/kapanis.png" alt="Closing round: task and decision rows with Done, Postpone, Approve buttons; beside it the Decisions and tasks panel and a task suggested from documents" width="100%"></p>

- **Tasks suggested from documents:** if documents added to your project contain work for you or your team, it shows up in the panel as a suggestion; approve it and it becomes a task, reject it and it is forgotten.
- **Open ends after a meeting:** a while after the meeting, if a task is still open or a question unanswered, the assistant gives a short reminder. It never runs in a private meeting.
- **Urgent meeting:** say *"Set up a twenty-minute meeting with Ali today"* and a ready-to-send invitation draft opens for Teams, Meet or Zoom. The invitation never goes out on its own.

## Today at a glance

In the morning the panel shows what is yours for the day at a glance: the day's focus, items awaiting your decision, and what is marked **New** or **Changed** since yesterday.
Every row has a one-click action beside it: *Approve*, *Done*, *Prepare the draft*. Overnight the assistant also looks through your records and writes down what it learned;
under *What I learned yesterday* you say **Right** or **Wrong**, and that is used next time.

<p align="center"><img src="gorsel/en/gun.png" alt="Today at a glance: the day's focus, items awaiting your decision (New, Changed), Prepare the draft, Approve, Done buttons; a What I learned yesterday row with Right and Wrong" width="100%"></p>

## Call your assistant by name

During setup you give your assistant a name; only that name appears on the panel, on cards and in speech. You type to it or ask
by voice: *"Defne, what date did we discuss for the beta last week?"* The answer arrives on the panel and aloud within seconds.

<p align="center"><img src="gorsel/en/mac.png" alt="Suflor.me Mac window: sidebar, cards and Defne's answer in the middle, agenda and live transcript on the right" width="100%"></p>

- **One box:** the same box sits under every view. `+` on the left adds a document, you type in the middle, and you hold the microphone
  on the right to ask by voice. Double-tap the microphone for a hands-free conversation.
- **Work for another session:** say *"Defne, forward this to the project session"* and the message is shown on a confirmation card;
  it is sent only if you approve.
- **Two assistants:** optionally add a second, more relaxed assistant for outside meetings. Turn it on in Settings and the two hear each
  other and join the conversation on their own; the three of you talk together.
- **Choice of AI:** the assistant's brain is Claude by default. Without a Claude subscription you can use a Gemini or OpenAI-compatible API key;
  each job (Talk, translation, project card) can be set separately.
  If the chosen service fails, that job is done once with Claude.
- **Voice:** your Mac's built-in voice, natural Turkish voices that run on your Mac (Pocket) or the optional Gemini voice.

## It remembers your project and its history

During setup you point it to your project folder. Suflor.me converts documents (Word, Pages, PDF, including old .doc and .rtf),
presentations (PowerPoint, Keynote), spreadsheets (Excel, Numbers, CSV) and images to text on this Mac and indexes them. Search goes beyond keywords: it finds passages close in meaning even when the words in your question never appear in the document.

<p align="center"><img src="gorsel/en/toplantilar.png" alt="Meetings window: a search for 'beta', eight results in four meetings" width="100%"></p>

- **Spreadsheets and the project card in one database:** Excel, Numbers and CSV sheets go into a small database on this Mac. For questions
  like "How much did we spend this month?" or "How many open items are there?", the assistant computes the answer instead of eyeballing
  rows, and names the source file. The project card you approve during setup (people, decisions, open items, each with its source) lives
  there too. The knowledge sits in a standard database, not in a file tied to one AI. The database is never written to your project folder.
- **Catches contradictions:** if a claim, number or responsibility in the conversation differs from an earlier document or meeting,
  it tells you, with the source.
- **Decision graph:** decisions and claims accumulate on this Mac. If the same person gives a different number at the next meeting,
  it's noticed.
- **Meetings window:** all transcripts in one place; search across transcripts and summaries, and a result opens the matching line.
- **A dictionary that learns:** names and terms that are mis-transcribed become dictionary candidates as you correct them or the assistant notices; once you approve, they come out right in the next meeting. You can undo any of them.
- **Speaker names:** names from the meeting app's captions are matched to each person's voiceprint on this Mac. Even without captions
  (desktop meeting, a recording dropped in later) the speaker's name is found.

## Privacy

Suflor.me was built around one rule from day one: **audio never leaves your Mac.** Speech recognition, voiceprints, document
conversion and search all run on this Mac.

<p align="center"><img src="gorsel/en/gizlilik.png" alt="What stays on your Mac, what goes to Claude, and what goes to Google only if you turn it on" width="100%"></p>

- Suflor.me's local server only accepts connections from this Mac (`127.0.0.1`). Meeting content is not sent to any server.
- The text sent to Claude goes through your own Claude Code session; Anthropic's terms of use apply.
- If you pick another service instead of Claude, the text context (transcript, notes, document passages) goes to that service; audio does not.
- The beta is voluntary development participation and can't be turned off. A copy of every package sent is kept in
  `~/Library/Application Support/Suflor/teshis/gonderilen/`, so you can read exactly what was sent.
- Meeting files stay in your project folder. They contain people's names; treat them as internal documents.

## Where it works

| Meeting | How |
|---|---|
| Microsoft Teams, Google Meet (web) | With the Chrome extension |
| Zoom (web) | Not for now — use the Zoom desktop app |
| Teams and Zoom desktop apps | With the Suflor.me Mac app (menu bar) |

The panel opens in two places: in the Suflor.me Mac app's window or in Chrome. The Mac window has a sidebar (Now · Today · Archive),
separate Settings and Help windows, and light/dark themes. The interface is available in Turkish and English.

## Installation

**1.** Paste into Terminal:

```bash
curl -fsSL https://raw.githubusercontent.com/suflorme/suflor/main/kur.sh | bash
```

**2.** The setup wizard opens in your browser. One task per screen: Mac check, AI connection (Claude or API key), your name, the assistant's name and
voice, project folder, model downloads, calendar and the Chrome extension. The wizard checks every step itself. If you close it, the
same command picks up where you left off.

**3.** Join a meeting. Press **Start** in the panel's calendar; the assistant takes it from there.

<p align="center"><img src="gorsel/en/sihirbaz.png" alt="Setup wizard: Name your assistant" width="72%"></p>

Every release is signed with the developer's key. Installation and updates verify the downloaded code's signature and install nothing
if it doesn't match. When a new version is out, an **Update** button appears on the panel.

### Requirements

| What | Required |
|---|---|
| Mac | Apple Silicon (M series), macOS 14 or later |
| Memory | at least 16 GB (about 4 GB in use during a meeting) |
| Disk | about 12 GB free (models about 5 GB; document conversion and search about 3.3 GB) |
| Browser | Google Chrome |
| AI | Recommended: [Claude Code](https://claude.com/claude-code) and a Claude subscription (Pro or higher). The wizard installs Claude Code if needed; sign in once in Terminal with `claude` → `/login`. Alternatives: a Gemini or OpenAI-compatible API key. |

## Shortcuts

| Shortcut | What it does |
|---|---|
| Option + Shift + K | Evidence: saves a picture of the meeting screen (warns if a password is visible; automatic while a screen is shared) |
| Option + Shift + O | What do I say? A one-sentence line |
| Option + Shift + M | Quiet: no cards for 10 minutes |
| Option + Shift + S | Silence the assistant |
| Option + Shift + Space (hold) | Ask the assistant by voice anywhere on your Mac (with the Mac app) |

## More

The detailed guide [KILAVUZ.md](KILAVUZ.md) (in Turkish) covers next steps after installation, project preparation, settings,
voices (Pocket, Gemini), privacy details and the list of components.

## License

MIT, see [LICENSE](LICENSE). Optional voice models are downloaded separately and come with their own licenses
([Guide → Lisanslar](KILAVUZ.md#lisanslar)).
