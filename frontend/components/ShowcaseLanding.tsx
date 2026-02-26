import Link from 'next/link'
import { AutoplayVideo } from './AutoplayVideo'

function PhoneMockup() {
  return (
    <div className="w-[280px] md:w-[300px] mx-auto">
      {/* Phone frame */}
      <div className="bg-white rounded-[2rem] shadow-xl border border-[rgba(0,0,0,0.08)] overflow-hidden">
        {/* Status bar */}
        <div className="bg-[#f6f6f6] px-6 pt-3 pb-1">
          <div className="flex items-center justify-between text-[10px] text-gray-500">
            <span>9:41</span>
            <div className="flex gap-1 items-center">
              <div className="w-3.5 h-2 border border-gray-400 rounded-sm relative">
                <div className="absolute inset-[1px] right-[2px] bg-gray-400 rounded-[1px]" />
              </div>
            </div>
          </div>
        </div>

        {/* Contact header */}
        <div className="bg-[#f6f6f6] px-4 pb-2 text-center border-b border-[rgba(0,0,0,0.06)]">
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-terracotta to-amber-400 mx-auto mb-1 flex items-center justify-center text-white text-xs font-semibold">M</div>
          <p className="text-sm font-semibold text-gray-900">Mira</p>
        </div>

        {/* Messages */}
        <div className="bg-white px-3 py-4 space-y-2.5 min-h-[320px]">
          {/* User message with photo */}
          <div className="flex justify-end">
            <div className="max-w-[85%]">
              <div className="bg-[#007AFF] rounded-2xl rounded-br-md px-3 py-2">
                {/* Photo thumbnail */}
                <div className="w-full h-24 rounded-lg bg-gradient-to-br from-stone-300 to-stone-400 mb-1.5 flex items-center justify-center">
                  <svg className="w-6 h-6 text-white/60" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0022.5 18.75V5.25A2.25 2.25 0 0020.25 3H3.75A2.25 2.25 0 001.5 5.25v13.5A2.25 2.25 0 003.75 21z" />
                  </svg>
                </div>
                <p className="text-white text-[13px] leading-snug">thinking about this for dinner tonight</p>
              </div>
            </div>
          </div>

          {/* Mira response */}
          <div className="flex justify-start">
            <div className="max-w-[85%]">
              <div className="bg-[#E9E9EB] rounded-2xl rounded-bl-md px-3 py-2">
                <p className="text-gray-900 text-[13px] leading-snug">
                  The shoes are too casual for what the top is doing. Do you have a heel or a mule?
                </p>
              </div>
            </div>
          </div>

          {/* User follow-up with photo */}
          <div className="flex justify-end">
            <div className="max-w-[85%]">
              <div className="bg-[#007AFF] rounded-2xl rounded-br-md px-3 py-2">
                <div className="w-full h-16 rounded-lg bg-gradient-to-br from-amber-200 to-amber-300 mb-1.5 flex items-center justify-center">
                  <svg className="w-5 h-5 text-white/60" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0022.5 18.75V5.25A2.25 2.25 0 0020.25 3H3.75A2.25 2.25 0 001.5 5.25v13.5A2.25 2.25 0 003.75 21z" />
                  </svg>
                </div>
                <p className="text-white text-[13px] leading-snug">these?</p>
              </div>
            </div>
          </div>

          {/* Mira final response */}
          <div className="flex justify-start">
            <div className="max-w-[85%]">
              <div className="bg-[#E9E9EB] rounded-2xl rounded-bl-md px-3 py-2">
                <p className="text-gray-900 text-[13px] leading-snug font-medium">
                  Yes. Go.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Input bar */}
        <div className="bg-white px-3 pb-4 pt-1 border-t border-[rgba(0,0,0,0.06)]">
          <div className="flex items-center gap-2">
            <div className="flex-1 bg-[#f2f2f7] rounded-full px-3 py-1.5">
              <p className="text-gray-400 text-[13px]">Text Message</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export function ShowcaseLanding() {
  return (
    <div className="min-h-screen bg-bone">
      {/* Hero Section */}
      <div className="max-w-4xl mx-auto px-4 pt-10 md:pt-20 pb-8 md:pb-16">
        <div className="md:flex md:items-center md:gap-12">
          {/* Copy */}
          <div className="md:w-1/2 text-center md:text-left mb-8 md:mb-0">
            <h1 className="text-3xl md:text-5xl mb-4 tracking-tight">Mira</h1>
            <p className="text-xl md:text-2xl text-ink leading-relaxed mb-3">
              You have the clothes. You just need a second opinion.
            </p>
            <p className="text-muted text-base md:text-lg leading-relaxed mb-8 max-w-md mx-auto md:mx-0">
              Text Mira a photo of what you&apos;re wearing. She knows your closet, your taste, and what actually works. Texts back in seconds.
            </p>
            <div className="max-w-xs mx-auto md:mx-0">
              <Link
                href="/get-started"
                className="block w-full bg-terracotta text-white text-center py-3.5 md:py-4 px-6 rounded-lg font-medium hover:opacity-90 transition active:opacity-80 min-h-[48px] flex items-center justify-center"
              >
                Meet Mira
              </Link>
            </div>
          </div>

          {/* Phone mockup */}
          <div className="md:w-1/2">
            <PhoneMockup />
          </div>
        </div>
      </div>

      {/* Proof — What it sounds like */}
      <div className="bg-white border-y border-[rgba(26,22,20,0.06)]">
        <div className="max-w-3xl mx-auto px-4 py-12 md:py-16">
          <h2 className="text-center text-2xl md:text-3xl mb-10 md:mb-14">What it sounds like</h2>

          <div className="space-y-12 md:space-y-16">
            {/* Card 1: Back and forth */}
            <div className="md:flex md:items-center md:gap-10">
              <div className="md:w-1/2 mb-6 md:mb-0">
                <div className="bg-bone rounded-xl overflow-hidden border border-[rgba(26,22,20,0.06)]">
                  <div className="aspect-[9/16]">
                    <AutoplayVideo
                      src="/showcase/sms-iterate.mp4"
                      className="w-full h-full object-cover object-top"
                    />
                  </div>
                </div>
              </div>
              <div className="md:w-1/2">
                <h3 className="text-xl md:text-2xl mb-3">Push back until you love it</h3>
                <p className="text-muted text-base leading-relaxed mb-0">
                  Text a request, get a styled outfit back in seconds. Don&apos;t love something? Say so — Mira iterates until the look is right.
                </p>
              </div>
            </div>

            {/* Card 2: Instagram inspo */}
            <div className="md:flex md:items-center md:gap-10 md:flex-row-reverse">
              <div className="md:w-1/2 mb-6 md:mb-0">
                <div className="bg-bone rounded-xl overflow-hidden border border-[rgba(26,22,20,0.06)]">
                  <div className="aspect-[9/16]">
                    <AutoplayVideo
                      src="/showcase/sms-inspo.mp4"
                      className="w-full h-full object-cover object-top"
                    />
                  </div>
                </div>
              </div>
              <div className="md:w-1/2">
                <h3 className="text-xl md:text-2xl mb-3">Saw a look you love? Send it.</h3>
                <p className="text-muted text-base leading-relaxed mb-0">
                  Send an Instagram photo. Mira maps it to pieces you already own and shows you exactly how to wear it.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* How It Works */}
      <div className="max-w-3xl mx-auto px-4 py-12 md:py-16">
        <h2 className="text-center text-2xl md:text-3xl mb-10 md:mb-14">How to get started</h2>

        <div className="max-w-lg mx-auto space-y-8">
          {[
            {
              step: '1',
              title: 'Tell Mira who you are',
              description: 'Your style in three words, what you want to feel like, what you feel uncomfortable with. Takes 2 minutes.',
            },
            {
              step: '2',
              title: 'Show her your closet',
              description: 'Upload photos of what you actually wear. The more she sees, the more specific she gets.',
            },
            {
              step: '3',
              title: 'Text her when you need her',
              description: 'Before you leave. At the store. Anytime you\u2019re not sure. She texts back.',
            },
          ].map((item) => (
            <div key={item.step} className="flex gap-4">
              <div className="shrink-0 w-8 h-8 rounded-full bg-terracotta text-white flex items-center justify-center text-sm font-semibold">
                {item.step}
              </div>
              <div>
                <h3 className="text-lg font-medium mb-1">{item.title}</h3>
                <p className="text-muted text-base leading-relaxed">{item.description}</p>
              </div>
            </div>
          ))}
        </div>

        <p className="text-center text-muted text-sm mt-8">
          Most people finish setup in one Sunday morning. After that, it&apos;s just texting.
        </p>
      </div>

      {/* She remembers everything */}
      <div className="bg-white border-y border-[rgba(26,22,20,0.06)]">
        <div className="max-w-3xl mx-auto px-4 py-12 md:py-16">
          <div className="md:flex md:items-center md:gap-10">
            <div className="md:w-1/2 mb-6 md:mb-0">
              <div className="bg-bone rounded-xl overflow-hidden border border-[rgba(26,22,20,0.06)]">
                <div className="aspect-[4/5]">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src="/showcase/wardrobe.png"
                    alt="Your closet, organized and remembered"
                    className="w-full h-full object-cover object-top"
                    loading="lazy"
                  />
                </div>
              </div>
            </div>
            <div className="md:w-1/2">
              <h3 className="text-xl md:text-2xl mb-3">She remembers everything</h3>
              <p className="text-muted text-base leading-relaxed">
                The white blazer you keep almost wearing. The jeans that go with everything.
                The look you saved last week. Mira knows what&apos;s in your closet and what you actually reach for.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Social Proof */}
      <div className="max-w-3xl mx-auto px-4 py-12 md:py-16">
        <div className="max-w-xl mx-auto space-y-8">
          <blockquote className="text-center">
            <p className="text-lg md:text-xl font-serif italic text-ink leading-relaxed">
              &ldquo;It reminded me of clothes I forgot I had&rdquo;
            </p>
          </blockquote>
          <blockquote className="text-center">
            <p className="text-lg md:text-xl font-serif italic text-ink leading-relaxed">
              &ldquo;I dreamt about it after my first session&rdquo;
            </p>
          </blockquote>
        </div>
      </div>

      {/* Bottom CTA */}
      <div className="bg-white border-t border-[rgba(26,22,20,0.06)]">
        <div className="max-w-md mx-auto px-4 py-12 md:py-16 text-center">
          <h2 className="text-2xl md:text-3xl mb-3">Your closet, your style, your Mira.</h2>
          <p className="text-muted text-base mb-8 leading-relaxed">
            20 minutes once. Then it&apos;s just texting.
          </p>
          <Link
            href="/get-started"
            className="block w-full bg-terracotta text-white text-center py-3.5 md:py-4 px-6 rounded-lg font-medium hover:opacity-90 transition active:opacity-80 min-h-[48px] flex items-center justify-center"
          >
            Meet Mira
          </Link>
        </div>
      </div>

      {/* Footer */}
      <footer className="border-t border-[rgba(26,22,20,0.06)] py-8">
        <div className="max-w-3xl mx-auto px-4 text-center">
          <p className="text-sm text-muted">
            Built by{' '}
            <a
              href="https://www.linkedin.com/in/peichin/"
              target="_blank"
              rel="noopener noreferrer"
              className="text-terracotta hover:underline"
            >
              Pei-Chin
            </a>
          </p>
        </div>
      </footer>
    </div>
  )
}
