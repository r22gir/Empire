'use client';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';

export default function StreamingMessage({ content }: { content: string }) {
  return (
    <div className="msg-in flex justify-start">
      <div
        className="max-w-[82%] rounded-2xl rounded-bl-sm px-4 py-3"
        style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}
      >
        {!content ? (
          <div className="flex items-center gap-3 py-1">
            <div className="flex items-center gap-1.5">
              {[0, 1, 2].map(i => (
                <span
                  key={i}
                  className="w-2 h-2 rounded-full animate-bounce"
                  style={{
                    background: 'linear-gradient(135deg, #D4AF37, #F0C842)',
                    animationDelay: `${i * 0.18}s`,
                    boxShadow: '0 0 6px rgba(212,175,55,0.4)',
                  }}
                />
              ))}
            </div>
            <div
              className="typing-shimmer"
              style={{ width: '80px', height: '4px', background: 'rgba(212,175,55,0.12)', borderRadius: '9999px' }}
            />
          </div>
        ) : (
          <div className="chat-markdown">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                code({ className, children }) {
                  const match = /language-(\w+)/.exec(className || '');
                  const str   = String(children).replace(/\n$/, '');
                  const block = match || str.includes('\n');
                  return block ? (
                    <SyntaxHighlighter
                      style={oneDark}
                      language={match?.[1] || 'text'}
                      PreTag="div"
                      customStyle={{
                        background: '#0d0d1f',
                        borderRadius: '8px',
                        fontSize: '12.5px',
                        margin: '0.5em 0',
                        border: '1px solid rgba(139,92,246,0.2)',
                      }}
                    >
                      {str}
                    </SyntaxHighlighter>
                  ) : (
                    <code
                      className="px-1.5 py-0.5 rounded text-xs font-mono"
                      style={{ background: 'var(--purple-pale)', color: '#c4b0ff', border: '1px solid var(--purple-border)' }}
                    >
                      {children}
                    </code>
                  );
                },
                table({ children }) {
                  return <div className="overflow-x-auto my-2"><table className="border-collapse w-full text-sm">{children}</table></div>;
                },
                th({ children }) {
                  return <th style={{ background: 'var(--elevated)', color: 'var(--gold)', borderColor: 'var(--border)' }} className="border px-3 py-1.5 text-left font-semibold">{children}</th>;
                },
                td({ children }) {
                  return <td style={{ borderColor: 'var(--border)' }} className="border px-3 py-1.5">{children}</td>;
                },
              }}
            >
              {content}
            </ReactMarkdown>
            <span className="streaming-cursor" />
          </div>
        )}
      </div>
    </div>
  );
}
