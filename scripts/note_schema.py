"""Generic ASK note frontmatter rules (machine validation data).

This module is data only. ASK parses it with ast.literal_eval and never imports
or executes it, so a staged or edited copy cannot run code during validation.
Keep SCHEMA a single literal: dicts, lists, strings, numbers, True/False/None.
Owners may extend enum values; docs/schema.md documents the supported subset.
"""

SCHEMA = {
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "ASK note frontmatter",
  "description": "Flat YAML frontmatter for ASK Markdown notes. The ASK validator implements only the subset documented in docs/schema.md; it is not a general JSON Schema engine.",
  "type": "object",
  "required": [
    "title",
    "description",
    "kind",
    "scope",
    "lifecycle_status",
    "updated"
  ],
  "additionalProperties": False,
  "properties": {
    "title": {
      "type": "string",
      "minLength": 1,
      "description": "Human-readable note title. Unique across the vault."
    },
    "description": {
      "type": "string",
      "minLength": 1,
      "description": "One-sentence summary used for routing and graph export."
    },
    "kind": {
      "type": "string",
      "enum": [
        "index",
        "date",
        "rule",
        "reference",
        "note",
        "decision",
        "project",
        "person",
        "schema",
        "task-list",
        "daily-plan",
        "log",
        "memory",
        "template",
        "codebase",
        "artifact",
        "registry",
        "loop",
        "skill",
        "prompt",
        "research"
      ],
      "description": "Note type. Paths ending in INDEX.md require index; non-index notes under Agents/rules/ require rule."
    },
    "scope": {
      "type": "string",
      "enum": [
        "shared",
        "personal",
        "work",
        "side"
      ],
      "description": "Area of life or work the note belongs to."
    },
    "lifecycle_status": {
      "type": "string",
      "enum": [
        "draft",
        "active",
        "stable",
        "archived",
        "empty",
        "placeholder",
        "needs-update"
      ],
      "description": "Maintenance state of the note."
    },
    "updated": {
      "type": "string",
      "format": "date",
      "description": "Last meaningful update as an ISO calendar date (YYYY-MM-DD)."
    },
    "tags": {
      "type": "array",
      "items": {
        "type": "string",
        "minLength": 1,
        "enum": [
          "agents",
          "bootstrap",
          "capabilities",
          "communications",
          "continuity",
          "daily",
          "delegation",
          "goals",
          "index",
          "integrations",
          "logs",
          "loops",
          "memory",
          "monthly",
          "ontology",
          "people",
          "personal",
          "plugins",
          "projects",
          "roster",
          "routing",
          "rules",
          "runtimes",
          "schema",
          "skills",
          "structure",
          "tasks",
          "taxonomy",
          "weekly"
        ]
      },
      "minItems": 1,
      "uniqueItems": True,
      "description": "Registered retrieval facets; extend this local enum or an applicable path rule with owner direction."
    },
    "aliases": {
      "type": "array",
      "items": {
        "type": "string",
        "minLength": 1
      },
      "minItems": 1,
      "uniqueItems": True,
      "description": "Alternative names for the note, as used by Obsidian."
    },
    "cssclasses": {
      "type": "array",
      "items": {
        "type": "string",
        "minLength": 1
      },
      "minItems": 1,
      "uniqueItems": True,
      "description": "Obsidian CSS classes applied when the note is rendered."
    },
    "project": {
      "type": "string",
      "minLength": 1,
      "description": "Owner-defined project identifier."
    },
    "domain": {
      "type": "string",
      "minLength": 1,
      "description": "Owner-defined subject area."
    },
    "source": {
      "type": "string",
      "minLength": 1,
      "description": "Where the content came from: a URL, document, conversation, or agent session."
    },
    "canonical": {
      "type": "boolean",
      "description": "True when this note is the authoritative source for its topic."
    },
    "governed_by": {
      "type": "array",
      "items": {
        "type": "string",
        "format": "wikilink-note"
      },
      "minItems": 1,
      "uniqueItems": True,
      "description": "Rules or policies that constrain this note."
    },
    "depends_on": {
      "type": "array",
      "items": {
        "type": "string",
        "format": "wikilink-note"
      },
      "minItems": 1,
      "uniqueItems": True,
      "description": "Notes that must be read or remain valid for this note to hold."
    },
    "derived_from": {
      "type": "array",
      "items": {
        "type": "string",
        "format": "wikilink-note"
      },
      "minItems": 1,
      "uniqueItems": True,
      "description": "Notes this note was produced from."
    },
    "associated_with": {
      "type": "array",
      "items": {
        "type": "string",
        "format": "wikilink-note"
      },
      "minItems": 1,
      "uniqueItems": True,
      "description": "Related notes without a stronger relation."
    },
    "date": {
      "type": "string",
      "format": "date"
    },
    "month": {
      "type": "string",
      "format": "month"
    },
    "plan_status": {
      "type": "string",
      "enum": [
        "planned",
        "active",
        "completed",
        "cancelled",
        "committed"
      ]
    },
    "relationship_status": {
      "type": "string",
      "enum": [
        "active",
        "cold",
        "waiting",
        "warm"
      ]
    },
    "loop_status": {
      "type": "string",
      "enum": [
        "active",
        "draft",
        "paused",
        "retired"
      ]
    },
    "capability_status": {
      "type": "string",
      "enum": [
        "active",
        "blocked",
        "legacy",
        "retired"
      ]
    },
    "contexts": {
      "type": "array",
      "items": {
        "type": "string",
        "minLength": 1
      },
      "minItems": 1,
      "uniqueItems": True
    },
    "repositories": {
      "type": "array",
      "items": {
        "type": "string",
        "minLength": 1,
        "format": "repository-url"
      },
      "minItems": 1,
      "uniqueItems": True
    }
  },
  "x-ask-path-rules": [
    {
      "glob": "Agents/**",
      "properties": {
        "scope": {
          "type": "string",
          "enum": [
            "shared"
          ]
        }
      }
    },
    {
      "glob": "Agents/hats/*.md",
      "exclude": [
        "**/INDEX.md"
      ],
      "properties": {
        "kind": {
          "type": "string",
          "enum": [
            "reference"
          ]
        }
      }
    },
    {
      "glob": "Agents/capabilities/**",
      "properties": {
        "kind": {
          "type": "string",
          "enum": [
            "index",
            "date",
            "reference",
            "note",
            "decision",
            "project",
            "person",
            "schema",
            "task-list",
            "daily-plan",
            "log",
            "memory",
            "template",
            "codebase",
            "artifact",
            "registry",
            "loop",
            "skill",
            "prompt",
            "research"
          ],
          "description": "Note type. Paths ending in INDEX.md require index; non-index notes under Agents/rules/ require rule."
        }
      }
    },
    {
      "glob": "Agents/loops/**",
      "exclude": [
        "**/INDEX.md"
      ],
      "required": [
        "loop_status"
      ],
      "optional": [
        "lifecycle_status"
      ],
      "forbidden": [
        "lifecycle_status"
      ],
      "properties": {
        "kind": {
          "type": "string",
          "enum": [
            "loop"
          ]
        }
      }
    },
    {
      "glob": "Agents/capabilities/skills/*/*.md",
      "exclude": [
        "**/INDEX.md"
      ],
      "required": [
        "capability_status"
      ],
      "optional": [
        "lifecycle_status"
      ],
      "forbidden": [
        "lifecycle_status"
      ],
      "properties": {
        "kind": {
          "type": "string",
          "enum": [
            "skill"
          ]
        },
        "scope": {
          "type": "string",
          "enum": [
            "shared",
            "work",
            "side"
          ]
        }
      }
    },
    {
      "glob": "Agents/capabilities/skills/shared/*.md",
      "exclude": [
        "**/INDEX.md"
      ],
      "forbidden": [
        "project"
      ],
      "properties": {
        "scope": {
          "type": "string",
          "enum": [
            "shared"
          ]
        }
      }
    },
    {
      "glob": "Personal/**",
      "forbidden": [
        "project"
      ],
      "properties": {
        "scope": {
          "type": "string",
          "enum": [
            "personal"
          ]
        }
      }
    },
    {
      "glob": "Projects/*/**/*.md",
      "exclude": [
        "Projects/Archive/**"
      ],
      "required": [
        "project"
      ],
      "properties": {
        "scope": {
          "type": "string",
          "enum": [
            "work",
            "side"
          ]
        }
      }
    },
    {
      "glob": "Projects/Archive/*/**/*.md",
      "required": [
        "project"
      ],
      "properties": {
        "scope": {
          "type": "string",
          "enum": [
            "work",
            "side"
          ]
        }
      }
    },
    {
      "glob": "Projects/Archive/INDEX.md",
      "forbidden": [
        "project"
      ],
      "properties": {
        "scope": {
          "type": "string",
          "enum": [
            "shared"
          ]
        }
      }
    },
    {
      "glob": "People/*/*.md",
      "exclude": [
        "**/INDEX.md"
      ],
      "required": [
        "contexts",
        "relationship_status"
      ],
      "optional": [
        "lifecycle_status"
      ],
      "forbidden": [
        "lifecycle_status",
        "domain"
      ],
      "properties": {
        "kind": {
          "type": "string",
          "enum": [
            "person"
          ]
        }
      }
    },
    {
      "glob": "People/personal/**",
      "forbidden": [
        "project"
      ],
      "properties": {
        "scope": {
          "type": "string",
          "enum": [
            "personal"
          ]
        }
      }
    },
    {
      "glob": "Tasks/Daily/*.md",
      "exclude": [
        "**/INDEX.md"
      ],
      "required": [
        "date",
        "plan_status"
      ],
      "optional": [
        "title",
        "description",
        "updated",
        "lifecycle_status"
      ],
      "forbidden": [
        "lifecycle_status"
      ],
      "properties": {
        "kind": {
          "type": "string",
          "enum": [
            "daily-plan"
          ]
        },
        "scope": {
          "type": "string",
          "enum": [
            "personal"
          ]
        }
      }
    },
    {
      "glob": "Memory/Logs/*.md",
      "exclude": [
        "**/INDEX.md"
      ],
      "required": [
        "month"
      ],
      "optional": [
        "title",
        "description",
        "updated",
        "lifecycle_status"
      ],
      "forbidden": [
        "lifecycle_status"
      ],
      "properties": {
        "kind": {
          "type": "string",
          "enum": [
            "log"
          ]
        },
        "scope": {
          "type": "string",
          "enum": [
            "personal"
          ]
        }
      }
    },
    {
      "glob": "Memory/Weekly/*.md",
      "exclude": [
        "**/INDEX.md"
      ],
      "properties": {
        "kind": {
          "type": "string",
          "enum": [
            "memory"
          ]
        },
        "scope": {
          "type": "string",
          "enum": [
            "personal"
          ]
        }
      }
    },
    {
      "glob": "Memory/Monthly/*.md",
      "exclude": [
        "**/INDEX.md"
      ],
      "properties": {
        "kind": {
          "type": "string",
          "enum": [
            "memory"
          ]
        },
        "scope": {
          "type": "string",
          "enum": [
            "personal"
          ]
        }
      }
    }
  ]
}
