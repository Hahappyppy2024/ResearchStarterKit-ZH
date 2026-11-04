// Keep maintained dates, adding newly collected venues without guessing deadlines.
export function mergeConferenceDeadlines(deadlines, catalog) {
  const rows = new Map(deadlines.map(c => [c.name.toLowerCase(), c]));
  for (const year of catalog.years || []) {
    for (const conference of year.conferences || []) {
      const name = conference.venue?.trim();
      if (!name || rows.has(name.toLowerCase())) continue;
      rows.set(name.toLowerCase(), {name, year:null, stages:[],
        note:'已收录于论文库；下一届主会投稿日期与官网链接待核实。'});
    }
  }
  return [...rows.values()];
}
