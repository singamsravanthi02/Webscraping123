import re

with open(r'c:\Users\saira\PROJECTMAIN\AI portal\frontend\src\app\dashboard\interviews\[id]\live\page.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    '  }, [cameraStatus]);',
    '  }, [cameraStatus, phase]);'
)

match = re.search(r'(?<=  return \(\n    <div ref=\{containerRef\} className=\"flex min-h-screen).*?(?=^}\n\nfunction StatusRow)', content, flags=re.DOTALL | re.MULTILINE)
if match:
    new_return = ''' flex-col bg-[#0b0b10] text-white overflow-hidden\">
      <iframe ref={jsRunnerRef} title=\"JavaScript runner\" sandbox=\"allow-scripts\" srcDoc={JS_RUNNER_SRC} onLoad={() => setRunnerReady(true)} className=\"hidden\" />

      <main className=\"flex-1 p-4 grid gap-4 lg:grid-cols-[1fr_320px] xl:grid-cols-[1fr_400px]\">
        <div className=\"relative rounded-3xl border border-white/10 bg-[#111118] overflow-hidden flex flex-col items-center justify-center\">
          <div className=\"relative flex items-center justify-center\">
            <div className={`absolute h-48 w-48 rounded-full bg-purple-500/20 blur-xl ${isSendingAnswer ? "animate-pulse" : ""}`} />
            <div className=\"relative flex h-32 w-32 items-center justify-center rounded-full border border-purple-500/30 bg-purple-500/10 backdrop-blur-md\">
              <Brain className=\"h-12 w-12 text-purple-300\" />
            </div>
          </div>
          
          <div className=\"absolute bottom-6 left-6 right-6 text-center\">
             <div className=\"bg-black/60 backdrop-blur-md border border-white/10 rounded-2xl p-4 inline-block max-w-2xl mx-auto shadow-2xl\">
                <p className=\"text-lg leading-relaxed text-white whitespace-pre-wrap\">
                  {currentQuestion || "Connecting..."}
                </p>
             </div>
          </div>

          <div className=\"absolute top-6 left-6 flex flex-wrap gap-2\">
            <div className=\"rounded-full bg-black/60 backdrop-blur-md border border-white/10 px-3 py-1.5 text-xs text-gray-300\">
              {meta.company} - {meta.difficulty}
            </div>
            <div className=\"rounded-full bg-purple-500/20 border border-purple-500/30 px-3 py-1.5 text-xs text-purple-300\">
              AI Interviewer
            </div>
          </div>
          
          {warningText && (
            <div className=\"absolute top-6 right-6 rounded-2xl bg-amber-500/10 border border-amber-500/20 px-4 py-2 text-xs text-amber-100 max-w-xs\">
              {warningText}
            </div>
          )}
        </div>

        <div className=\"flex flex-col gap-4 h-full\">
           <div className=\"relative h-64 rounded-3xl border border-white/10 bg-black overflow-hidden shrink-0\">
             <video ref={videoRef} autoPlay muted playsInline className=\"h-full w-full object-cover\" />
             <div className=\"absolute bottom-3 left-3 rounded-full bg-black/60 backdrop-blur-md border border-white/10 px-3 py-1 text-xs text-white\">
               You
             </div>
             {isRecording && (
                <div className=\"absolute top-3 right-3 flex items-center gap-2 rounded-full bg-red-500/20 border border-red-500/30 px-2 py-1 text-xs text-red-300\">
                  <div className=\"h-2 w-2 rounded-full bg-red-500 animate-pulse\" />
                  Recording
                </div>
             )}
           </div>

           <div className=\"flex-1 rounded-3xl border border-white/10 bg-[#111118] p-5 flex flex-col min-h-0\">
              {isCoding ? (
                 <div className=\"flex-1 flex flex-col min-h-0\">
                    <div className=\"flex justify-between items-center mb-3\">
                       <select value={codeLanguage} onChange={(e) => {
                          const nextLang = e.target.value as CodeLanguage;
                          setCodeLanguage(nextLang);
                          setCode(CODE_STARTERS[nextLang]);
                       }} className=\"bg-black/40 border border-white/10 rounded-full px-3 py-1 text-xs text-gray-300 outline-none\">
                          <option value=\"javascript\">JS</option>
                          <option value=\"python\">Python</option>
                          <option value=\"java\">Java</option>
                          <option value=\"cpp\">C++</option>
                       </select>
                       <div className=\"flex items-center gap-2\">
                          <button type=\"button\" onClick={runCode} disabled={isRunningCode} className=\"text-xs bg-white/5 border border-white/10 rounded-full px-3 py-1 hover:bg-white/10 flex items-center gap-1 disabled:opacity-50\">
                             {isRunningCode ? <Loader2 className=\"h-3 w-3 animate-spin\" /> : <Play className=\"h-3 w-3\" />}
                             Run Code
                          </button>
                       </div>
                    </div>
                    <div className=\"flex-1 rounded-2xl border border-white/10 overflow-hidden bg-[#07070a] min-h-0\">
                        <MonacoEditor
                          height=\"100%\"
                          language={codeLanguage === "cpp" ? "cpp" : codeLanguage}
                          theme=\"vs-dark\"
                          value={code}
                          onChange={(val) => setCode(val || "")}
                          options={{ minimap: { enabled: false }, fontSize: 13, wordWrap: "on" }}
                        />
                    </div>
                    {runLog.length > 0 && (
                      <div className=\"h-24 mt-3 rounded-xl border border-white/10 bg-[#07070a] p-2 overflow-y-auto font-mono text-[10px] text-sky-100 whitespace-pre-wrap\">
                         {runLog.join("\\n")}
                      </div>
                    )}
                 </div>
              ) : (
                 <form onSubmit={(e) => { e.preventDefault(); void submitAnswer(); }} className=\"flex-1 flex flex-col min-h-0\">
                    <div className=\"text-sm font-medium text-gray-400 mb-2 flex justify-between items-center\">
                       Text Fallback
                       <span className=\"text-xs text-gray-500\">Press Enter to submit</span>
                    </div>
                    <textarea 
                       value={inputText}
                       onChange={e => setInputText(e.target.value)}
                       onKeyDown={e => {
                          if (e.key === 'Enter' && !e.shiftKey) {
                             e.preventDefault();
                             void submitAnswer();
                          }
                       }}
                       placeholder=\"Type your answer if voice is unavailable...\"
                       className=\"flex-1 resize-none rounded-2xl border border-white/10 bg-black/20 p-4 text-sm leading-relaxed text-gray-300 outline-none focus:border-purple-500/30 transition-colors\"
                    />
                 </form>
              )}
           </div>
        </div>
      </main>

      <footer className=\"border-t border-white/10 bg-[#07070a] px-6 py-4 flex items-center justify-between\">
         <div className=\"flex items-center gap-4\">
           <div className=\"text-xl font-bold text-white tracking-widest\">{formatDuration(elapsedSeconds)}</div>
           <div className=\"h-4 w-px bg-white/20\" />
           <div className=\"text-sm text-gray-400\">Q {currentQuestionNumber}/{meta.questionTarget}</div>
           {violationCount > 0 && (
             <div className=\"ml-4 rounded-full border border-amber-500/30 bg-amber-500/10 px-2 py-1 text-xs text-amber-300\">
               {violationCount} warning{violationCount > 1 ? 's' : ''}
             </div>
           )}
         </div>

         <div className=\"flex items-center gap-4\">
            {canUseVoice && (
               <button type=\"button\" onClick={toggleRecording} className={`flex h-14 w-14 items-center justify-center rounded-full transition-all ${isRecording ? "bg-red-500 text-white hover:bg-red-600 shadow-[0_0_20px_rgba(239,68,68,0.4)]" : "bg-white/10 text-gray-300 hover:bg-white/20"}`}>
                 {isRecording ? <Mic className=\"h-6 w-6\" /> : <MicOff className=\"h-6 w-6\" />}
               </button>
            )}

            <button type=\"button\" onClick={() => void submitAnswer()} disabled={isSendingAnswer || (isCoding ? !code.trim() : !inputText.trim())} className=\"flex h-14 px-8 items-center justify-center gap-2 rounded-full bg-purple-600 text-white font-medium transition-all hover:bg-purple-500 disabled:opacity-50 disabled:cursor-not-allowed\">
               {isSendingAnswer ? <Loader2 className=\"h-5 w-5 animate-spin\" /> : <Send className=\"h-5 w-5\" />}
               Submit Answer
            </button>
         </div>

         <div className=\"flex items-center gap-3\">
            <button type=\"button\" onClick={() => void finishInterview()} className=\"flex items-center justify-center h-12 w-12 rounded-full bg-white/5 border border-white/10 text-red-400 hover:bg-red-500/10 hover:border-red-500/30 transition-all\" title=\"End Interview\">
               <StopCircle className=\"h-5 w-5\" />
            </button>
            <button type=\"button\" onClick={() => { if (!document.fullscreenElement) { void containerRef.current?.requestFullscreen?.(); } else { void document.exitFullscreen(); } }} className=\"flex items-center justify-center h-12 w-12 rounded-full bg-white/5 border border-white/10 text-gray-400 hover:bg-white/10 transition-all\" title=\"Toggle Fullscreen\">
               {isFullscreen ? <Minimize className=\"h-5 w-5\" /> : <Maximize className=\"h-5 w-5\" />}
            </button>
         </div>
      </footer>
    </div>
  );
'''
    content = content[:match.start()] + new_return + content[match.end():]
    with open(r'c:\Users\saira\PROJECTMAIN\AI portal\frontend\src\app\dashboard\interviews\[id]\live\page.tsx', 'w', encoding='utf-8') as f:
        f.write(content)
    print("UI replaced.")
else:
    print("Match not found.")
