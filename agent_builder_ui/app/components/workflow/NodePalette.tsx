export function NodePalette() {
  const onDragStart = (event: React.DragEvent, nodeType: string) => {
    event.dataTransfer.setData('application/reactflow', nodeType);
    event.dataTransfer.effectAllowed = 'move';
  };

  const nodeCategories = [
    {
      title: 'Data',
      nodes: [
        {
          type: 'database',
          icon: 'storage',
          label: 'Database',
          description: 'Connect to SQL databases'
        },
        {
          type: 'filter',
          icon: 'filter_alt',
          label: 'Select Data',
          description: 'Filter and select data'
        }
      ]
    },
    {
      title: 'Agents',
      nodes: [
        {
          type: 'agent',
          icon: 'smart_toy',
          label: 'Agent Node',
          description: 'AI processing node'
        }
      ]
    },
    {
      title: 'Output',
      nodes: [
        {
          type: 'output',
          icon: 'output',
          label: 'Output Node',
          description: 'Save processed data'
        }
      ]
    },
    {
      title: 'Logic',
      nodes: [
        {
          type: 'script',
          icon: 'code',
          label: 'Custom Script',
          description: 'Run custom code'
        },
        {
          type: 'conditional',
          icon: 'fork_right',
          label: 'Conditional',
          description: 'Branch workflow logic'
        }
      ]
    }
  ];

  return (
    <div className="space-y-4">
      {nodeCategories.map((category) => (
        <div key={category.title}>
          <h3 className="text-xs font-semibold uppercase text-gray-400 mb-2">
            {category.title}
          </h3>
          <div className="grid grid-cols-2 gap-3">
            {category.nodes.map((node) => (
              <div
                key={node.type}
                className="p-3 border border-[#374151] rounded-lg flex flex-col items-center justify-center space-y-2 cursor-pointer hover:bg-[#111a22] transition-colors group"
                draggable
                onDragStart={(event) => onDragStart(event, node.type)}
                title={node.description}
              >
                <span className="material-symbols-outlined text-[#1173d4] text-xl group-hover:scale-110 transition-transform">
                  {node.icon}
                </span>
                <span className="text-xs font-medium text-center text-white">
                  {node.label}
                </span>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}