import fs from 'node:fs'
import path from 'node:path'

function walk(directory) {
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap((entry) =>
    entry.isDirectory() ? walk(path.join(directory, entry.name)) : [path.join(directory, entry.name)],
  )
}

const files = walk('docs')
const badLinks = []
for (const file of files.filter((candidate) => candidate.endsWith('.md'))) {
  const source = fs.readFileSync(file, 'utf8')
  for (const match of source.matchAll(/\[[^\]]*\]\(([^)]+)\)/g)) {
    const target = match[1].split('#')[0]
    if (!target || /^[a-z]+:/i.test(target)) continue
    const resolved = path.resolve(path.dirname(file), target)
    if (!fs.existsSync(resolved)) badLinks.push(`${file} -> ${match[1]}`)
  }
}

if (badLinks.length) {
  console.error(badLinks.join('\n'))
  process.exit(1)
}

const diagrams = files.filter((file) => file.endsWith('.mmd'))
if (diagrams.length !== 14) {
  console.error(`Expected 14 Mermaid sources, found ${diagrams.length}`)
  process.exit(1)
}

console.log(`Documentation validation passed: ${files.length} files, ${diagrams.length} diagrams`)
