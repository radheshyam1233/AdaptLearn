# AdaptLearn | AI-Powered Adaptive Learning Platform

AdaptLearn helps students understand why they got an answer wrong and gives tutors a live view of where learners are struggling. It covers Python, SQL, statistics, and logic.

## Why I built this

In my first and second year at IIT (BHU), I worked as a Subject Matter Expert at Chegg India, writing step-by-step solutions for students. When generative AI made it easy to get an answer, I kept coming back to a problem I had seen as a student. You can follow a solution and still have trouble spotting the concept you missed.

That led me to a question. If answers are easy to get, what still helps students learn? I built AdaptLearn to help students understand their mistakes, practise the concepts they find difficult, and give tutors a way to see where learners need help.

## What it does

- **Student dashboard** opens after student sign-in. It shows the learner’s own attempts, accuracy, recent feedback and a recommended topic.
- **Practice** gives feedback tailored to the selected answer and recommends questions based on each topic's recent mistakes.
- **My progress** shows accuracy, coverage, and review priority. Recent mistakes contribute more to review priority than older mistakes.
- **Tutor dashboard** opens after tutor sign-in and uses the latest 1,000 attempts for concept error rates, recent activities, and learner review flags. A learner appears in the review list after at least two misses and a 50% or greater error rate for a topic.

React and Vite provide the UI. FastAPI grades account submissions and authenticates students and tutors with JWTs in HTTP-only cookies. MongoDB stores accounts and attempts. WebSockets refresh tutor dashboards as students submit answers. The optional Redis cache expires after 25 seconds and a new attempt advances the cache revision. Run one API process for the current live-event and cache design. Optional OpenAI calls generate wrong-answer hints using the question and selected option. If the call fails or takes too long, a curated hint remains available. Students and tutors sign in with an AdaptLearn account.

## Run locally

Install Node.js 22 and Python 3.12. Copy .env.example to .env, add a JWT secret of at least 32 random characters and a MongoDB connection string to enable accounts, and set COOKIE_SECURE=false for local HTTP.

    npm ci
    npm run build
    python -m pip install -r backend/requirements.txt
    python -m uvicorn backend.main:app --env-file .env --port 8000

Open http://localhost:8000, or http://localhost:8000/api/docs for the API reference. For a Docker build, run docker build -t adaptlearn . and docker run --env-file .env -p 8000:10000 adaptlearn. MongoDB and a JWT secret are required for account access.

## Deploy to Render and MongoDB Atlas

1. In Render, create a Blueprint from this repository. Select the render-rebuild branch. The Blueprint provisions one free Docker web service and generates JWT_SECRET. Render serves the React build and API from the same URL.
2. In Atlas, create or select a cluster and create a dedicated database user with readWrite access to adaptlearn. Copy the driver connection URI from that cluster. Use your database user's credentials and URL-encode reserved characters in them.
3. Open the Render service's **Connect → Outbound** tab. Add its outbound CIDR ranges to the Atlas project's IP access list.
4. In Render under **Environment**, add MONGODB_URI with the complete URI. MONGODB_DB defaults to adaptlearn. Save and deploy. Keep these values out of Git and chat.
5. Check that /health returns {"status":"ok"} and /api/status returns {"accounts":true}. Register a student and check that sign-in opens the Student dashboard. Submit an answer and reload to confirm the attempt persists. Create a tutor account and note its invite code. Create a student account with that code in a separate browser window, submit an answer, and confirm the tutor dashboard updates.
6. Optionally set OPENAI_API_KEY and REDIS_URL (redis:// or rediss://). The app labels curated hints and AI hints separately. The free Render service can take time to wake up after inactivity.

Official setup references are [Render Blueprints](https://render.com/docs/blueprint-spec), [Render outbound IP addresses](https://render.com/docs/outbound-ip-addresses), and [MongoDB Atlas and Render](https://www.mongodb.com/docs/atlas/reference/partner-integrations/render/).

### Student and tutor accounts

Choose **Student** or **Tutor** when creating an account. New tutors get an invite code on their dashboard. Students can enter the code at signup to join that tutor's classroom. Tutors see activity from their own classroom, and students can practice independently without a code. Previously provisioned tutors retain access to historical attempts.

## Résumé features and acceptance checks

| Résumé focus | Implementation and acceptance check |
| --- | --- |
| Full-stack learning platform with React.js, FastAPI, PostgreSQL, JWT auth and role-based access | The rebuild uses MongoDB Atlas for storage. Verify that a student signs in to a personal dashboard and can read only their own history. A tutor signs in to the tutor dashboard and can read classroom analytics. Protected API routes reject the other role. |
| OpenAI API analysis of wrong answers, personalised hints and weak concept tracking | Set OPENAI_API_KEY, submit an incorrect answer and check for an AI hint. Wrong answers increase the review priority for that topic. The student dashboard recommends the topic with the highest current review priority. Curated hints cover provider failures. |
| Live tutor dashboard using WebSockets, Redis caching and Docker deployment | With REDIS_URL configured, verify a repeat dashboard request uses the cache. Leave the tutor dashboard open and submit a student answer in another browser session. Verify a live refresh includes the new attempt and invalidates the previous cache entry. Use the Dockerfile and Render Blueprint for hosting. |

Describe storage as MongoDB Atlas when referring to the rebuild. Measure dashboard latency with and without Redis on the deployed service before citing a speed improvement.
