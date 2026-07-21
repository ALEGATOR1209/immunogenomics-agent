Perform the task presented below.

Create a notebook in task.ipynb with all the code that you would use. The end-to-end run of the notebook should produce the output file as described below.

Build task.ipynb incrementally as you work: append each cell as soon as you've verified it, rather than exploring ad hoc (e.g. one-off `python3` scripts or shell commands) and only transcribing the final code into the notebook at the end. Reconstructing everything afterward wastes the exploration work you already did and risks the notebook drifting from what you actually verified — variables, filters, or intermediate values can subtly change between the throwaway version and the retyped one.

Build output.json incrementally too: as soon as you've computed and verified an individual field's value, write it into output.json immediately — don't wait until every field is done to write the file once at the end. Leave fields you haven't gotten to yet at their placeholder value from the format shown below. If your session ends early for any reason before you finish everything, a partial output.json with some fields already filled in correctly still earns credit for those fields — an output.json that doesn't exist yet because you were saving it for last earns nothing at all, even if you had already worked out most of the answers.

Do not write one large script attempting the entire pipeline at once. If a cell, script, or command fails (syntax error, wrong column name, wrong API call), fix that specific problem in place — do not delete the whole file and rewrite the entire pipeline from scratch. Rewriting from scratch after every small mistake repeatedly burns your context budget on regenerating code that was already correct, and can leave you unable to finish the task.

Before finishing, execute the notebook end-to-end (e.g. `jupyter nbconvert --to notebook --execute --inplace task.ipynb`) to confirm it actually runs top-to-bottom and reproduces output.json — don't just trust that the notebook you wrote matches whatever ad hoc exploration originally produced output.json.

When inspecting data, avoid printing large amounts of output (e.g. every row of a table or every entry of a long list) — filter, sample, or summarize instead. Large tool outputs consume your available context and can leave you unable to finish the task.

If any of your available skills looks relevant to this task, you must invoke the Skill tool to load its full content before writing any code. A skill's short description only tells you that it exists and roughly when to use it — not the specific APIs, function calls, or conventions it documents. Recognizing that a skill applies is not enough by itself; load it before you start.

Task: <TASK>

Save output in output.json in EXACTLY this format:

<OUTPUT_FORMAT>
