import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import StatePanel from '../components/StatePanel.jsx'
import api from '../services/api.js'

function nodeLabel(type) {
  return { database_root: 'Database', connection: 'Service', database: 'Database', schema: 'Schema', table: 'Table', column: 'Column' }[type]
}

function childLabel(type) {
  return { database_root: 'Services', connection: 'Databases', database: 'Schemas', schema: 'Tables', table: 'Columns' }[type]
}

function metadataRows(node) {
  const rows = [
    ['Name', node.name],
    ['Type', nodeLabel(node.type)],
    ['Owner', node.created_by || '--'],
    ['Tags', node.tags?.length ? node.tags.join(', ') : '--'],
  ]
  if (node.data_type) rows.push(['Data type', node.data_type])
  if (typeof node.is_nullable === 'boolean') rows.push(['Nullable', node.is_nullable ? 'Yes' : 'No'])
  if (typeof node.ordinal_position === 'number') rows.push(['Ordinal position', node.ordinal_position])
  if (typeof node.is_primary_key === 'boolean') rows.push(['Primary key', node.is_primary_key ? 'Yes' : 'No'])
  rows.push(['Description', node.description || '--'])
  return rows
}

// data asset description
function childDescription(child) {
  return child.description || '--'
}

function childDataType(child) {
  return child.type === 'column' ? child.data_type || '--' : '--'
}

function findTreeNode(nodes, type, id) {
  for (const node of nodes) {
    if (node.type === type && String(node.id) === String(id)) return node
    const match = findTreeNode(node.children || [], type, id)
    if (match) return match
  }
  return null
}

function findTreePath(nodes, type, id, ancestors = []) {
  for (const node of nodes) {
    const path = [...ancestors, node]
    if (node.type === type && String(node.id) === String(id)) return path
    const match = findTreePath(node.children || [], type, id, path)
    if (match) return match
  }
  return null
}

function TreeNode({ node, expanded, onToggle, onSelect, selectedId }) {
  const hasChildren = node.type !== 'column' && node.children?.length > 0
  const isExpanded = expanded.has(`${node.type}-${node.id}`)

  return (
    <li>
      <div
        className={`metadata-tree-row ${selectedId === `${node.type}-${node.id}` ? 'selected' : ''}`}
      >
        {hasChildren ? 
        (
          <button
            className={`tree-toggle ${isExpanded ? 'expanded' : ''}`}
            type="button"
            aria-label={`${isExpanded ? 'Collapse' : 'Expand'} ${node.name}`}
            onClick={() => onToggle(node)}
          >
            <span aria-hidden="true" />
          </button>
        ) 
        : 
        <span className="tree-toggle-spacer" />
        }
       
        <button className="tree-name" type="button" onClick={() => onSelect(node)}>
          {node.name}
        </button>
      </div>

      {isExpanded && node.children?.length > 0 && (
        <ul>
          {node.children.map((child) => (
            <TreeNode
              key={`${child.type}-${child.id}`}
              node={child}
              expanded={expanded}
              onToggle={onToggle}
              onSelect={onSelect}
              selectedId={selectedId}
            />
          ))}
        </ul>
      )}
    </li>
  )
}

function MetadataExplorer() {
  const [searchParams] = useSearchParams()
  const [tree, setTree] = useState([])
  const [expanded, setExpanded] = useState(new Set())
  const [selected, setSelected] = useState(null)
  const [searchResults, setSearchResults] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)

  // Load the catalog tree and by deafult snoflake page opens
  useEffect(() => {
    let active = true
    async function loadConnections() {
      try {
        const response = await api.get('/api/catalog/tree')
        if (active) {
          const nextTree = response.data.services
          setTree(nextTree)
          if (!searchParams.get('q')) {
            const snowflake = nextTree.find((node) => node.name.toUpperCase() === 'SNOWFLAKE')
            if (snowflake) {
              setSelected(snowflake)
              setExpanded(new Set([`${snowflake.type}-${snowflake.id}`]))
            }
          }
        }
      } 
      catch {
        if (active) setError('The metadata catalog could not be loaded.')
      } 
    finally {
        if (active) setIsLoading(false)
      }
    }
    loadConnections()
    return () => { active = false }
  }, [searchParams])


  useEffect(() => {
    const query = searchParams.get('q')
    if (!query) {
      const resetTimer = window.setTimeout(() => setSearchResults([]), 0)
      return () => window.clearTimeout(resetTimer)
    }
    api.get('/api/metadata/search', 
      { params: { q: query, ...(searchParams.get('type') 
        ? { type: searchParams.get('type') } 
        : {}
      )}})
      .then((response) => setSearchResults(response.data)).
      catch(() => setSearchResults([]))
  }, [searchParams])


  useEffect(() => {
    const selectedType = searchParams.get('type')
    const selectedId = searchParams.get('id')
    const result = searchResults.find((item) => item.type === selectedType && String(item.id) === selectedId)
    const selectionTimer = window.setTimeout(() => {
      if (result) {
        setSelected(findTreeNode(tree, result.type, result.id) || result)
        const path = findTreePath(tree, result.type, result.id) || []
        setExpanded((current) => {
          const next = new Set(current)
          path.forEach((node) => next.add(`${node.type}-${node.id}`))
          return next
        })
      }
      else if (searchParams.get('q')) setSelected(null)
    }, 0)
    return () => window.clearTimeout(selectionTimer)
  }, [searchParams, searchResults, tree])


  async function toggleNode(node) {
    const key = `${node.type}-${node.id}`
    if (expanded.has(key)) {
      setExpanded((current) => { const next = new Set(current); next.delete(key); return next })
      return
    }
    setExpanded((current) => new Set(current).add(key))
  }


  function selectNode(node) {
    const treeNode = findTreeNode(tree, node.type, node.id) || node
    const path = findTreePath(tree, node.type, node.id) || []
    setSelected(treeNode)
    setExpanded((current) => {
      const next = new Set(current)
      path.forEach((ancestor) => next.add(`${ancestor.type}-${ancestor.id}`))
      return next
    })
  }

  const activeSelected = selected
  const showChildDataType = activeSelected?.type === 'table'

  return (
    <section className="metadata-page">
      
      <div className="metadata-heading">
        <div>
          <h1>Metadata explorer</h1>
          <p>Browse the structure of your connected data sources.</p>
        </div>
      </div>

      {isLoading && <StatePanel type="loading" title="Loading catalog" description="Retrieving connected data sources." />}
      {!isLoading && error && <StatePanel type="error" title="Catalog unavailable" description={error} />}
      {!isLoading && !error && 
        <div className="metadata-workspace">
         
          {/* catalog tree */}
          <aside className="metadata-tree">
            <div className="tree-heading">
              <div><strong>Catalog tree</strong></div>
            </div>
            {tree.length === 0 ? (
              <p className="tree-empty">No databases configured.</p>
            ) : (
              <ul>
                {tree.map((node) => (
                  <TreeNode
                    key={`${node.type}-${node.id}`}
                    node={node}
                    expanded={expanded}
                    onToggle={toggleNode}
                    onSelect={selectNode}
                    selectedId={activeSelected && `${activeSelected.type}-${activeSelected.id}`}
                  />
                ))}
              </ul>
            )}
          </aside>
             

          {/* metadata area */}
          <main className="metadata-detail">{activeSelected ? 
            <>
              <div className="metadata-detail-heading"><div><span className="metadata-kicker">{nodeLabel(activeSelected.type)}</span><h2>{activeSelected.name}</h2></div></div>
              
              {/* metadata card grid  */}
              <div className="metadata-card-grid">
                {metadataRows(activeSelected).map(([field, value]) => 
                  <article className={`detail-card ${field === 'Description' ? 'metadata-description-card' : ''}`} key={field}>
                    <span>{field}</span>
                    <strong>{value}</strong>
                  </article>)}
              </div>

              {/* child data asset's metadata table */}
              {activeSelected.children?.length > 0 && 
              <div className="metadata-columns">
                <div className="section-heading"><div><h3>{childLabel(activeSelected.type)}</h3></div><span className="section-caption">{activeSelected.children.length} items</span></div>
                <div className="table-wrap metadata-children-table">
                  <table>
                    <thead>
                      <tr>
                        <th>Name</th>
                        <th>Type</th>
                        {showChildDataType && <th>Data type</th>}
                        <th>Description</th>
                        <th>Owner</th>
                        <th>Tags</th>
                      </tr>
                    </thead>
                    <tbody>
                      {activeSelected.children.map((child) => (
                        <tr
                          key={`${child.type}-${child.id}`}
                          className="metadata-child-row"
                          onClick={() => selectNode(child)}
                        >
                          <td className="table-primary">{child.name}</td>
                          <td>{nodeLabel(child.type)}</td>
                          {showChildDataType && <td>{childDataType(child)}</td>}
                          <td>{childDescription(child)}</td>
                          <td>{child.created_by || '--'}</td>
                          <td>{child.tags?.length ? child.tags.join(', ') : '--'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>}
            </> 
            : 
            <div className="metadata-detail-empty">
              <span className="tree-type tree-type-database">M</span>
              <h2>Select an item</h2>
              <p>Choose a database, service, schema, table, or column to inspect its metadata and children.</p>
            </div>}

          </main>
        </div>}
    </section>
  )
}

export default MetadataExplorer