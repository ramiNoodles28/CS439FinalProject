yo

tooltip
- handles hover interaction, and display tooltip

filterMenu
- allows user to select filters

mainPlot
- display data based on filtered data

core
- cleans data, standardizes scores/weights respectively and hold school information by row for easy access and implementation by each section
- also sets current state of user selection
- store.update changes current state and each section redraws

main
- runs through sepearate sections and adds them to the full application
- calls build(fig, spec) once and then after every change rows are computed it calls render(rows, state)

cost_earnings
- displays cost vs earnings chart and highlights schools within budget of the user
