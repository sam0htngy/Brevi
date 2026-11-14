import { SignInButton, useAuth } from '@clerk/clerk-react';
import { Link } from 'react-router-dom';

const steps = [
  ['Drop in a video', 'Start with a lecture, interview, or recording from your device.'],
  ['Find the key moments', 'Brevi’s video summarization is designed to pick out the parts that carry the story.'],
  ['Watch the highlights', 'Catch up on the main ideas in a shorter cut you can revisit.'],
];

function StartButton({ primary = false }: { primary?: boolean }) {
  const { isLoaded, isSignedIn } = useAuth();
  const className = primary ? 'button button-primary' : 'button button-outline';

  if (isSignedIn) {
    return <Link className={className} to="/upload">Upload a video <span aria-hidden="true">↗</span></Link>;
  }

  return (
    <SignInButton mode="modal" forceRedirectUrl="/upload" signUpForceRedirectUrl="/upload">
      <button className={className} disabled={!isLoaded}>
        {primary ? 'Get started' : 'Sign in'} <span aria-hidden="true">↗</span>
      </button>
    </SignInButton>
  );
}

export default function Login() {
  return (
    <div className="site">
      <header className="site-header shell">
        <Link className="wordmark" to="/" aria-label="Brevi home">brevi<span>.</span></Link>
        <nav aria-label="Main navigation">
          <a className="nav-link" href="#how-it-works">How it works</a>
          <StartButton />
        </nav>
      </header>
      <main>
        <section className="hero shell" aria-labelledby="hero-title">
          <div>
            <p className="eyebrow">Video summarization</p>
            <h1 id="hero-title">Long videos.<br /><em>Short highlights.</em></h1>
            <p className="intro">Turn a full-length video into a short highlight reel so you can get straight to the moments that matter.</p>
            <StartButton primary />
          </div>
          <figure className="demo">
            <figcaption>Example summary</figcaption>
            <div className="demo-source">
              <div className="demo-heading"><span>Original recording</span><time dateTime="PT24M18S">24:18</time></div>
              <div className="timeline" aria-hidden="true"><i /><i /><i /></div>
            </div>
            <div className="demo-arrow" aria-hidden="true">↓</div>
            <div className="demo-result">
              <div className="demo-heading"><span>Highlight reel</span><time dateTime="PT2M42S">02:42</time></div>
              <ul>
                <li><time dateTime="PT1M42S">01:42</time> The main question</li>
                <li><time dateTime="PT8M16S">08:16</time> A practical example</li>
                <li><time dateTime="PT21M3S">21:03</time> The closing takeaway</li>
              </ul>
            </div>
          </figure>
        </section>
        <section className="how shell" id="how-it-works" aria-labelledby="how-title">
          <h2 id="how-title">How Brevi works</h2>
          <ol className="steps" role="list">
            {steps.map(([title, description]) => (
              <li key={title}>
                <h3>{title}</h3>
                <p>{description}</p>
              </li>
            ))}
          </ol>
        </section>
      </main>
    </div>
  );
}
