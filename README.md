# Team 07 - Parser & Syntax-Directed Translation

Parser and Syntax-Directed Translation (SDT) project developed for the Compilers course at the Faculty of Engineering, UNAM.

## Project Objective

Develop a Bottom-Up CLR(1) parser integrated with the lexical analyzer developed in the previous project.

The parser will analyze a broad defined subset of the C programming language and perform syntax and semantic validation through Syntax-Directed Translation (SDT) rules.

The objective is to support as many relevant C language constructs as possible within the scope of the project.

## Parsing Method

The selected parsing method is **CLR(1) - Canonical LR(1)**.

CLR(1) was selected mainly because it provides greater parsing power and precision than LR(0) and SLR(1), allowing the project to support a broader subset of the C programming language.

CLR(1) uses LR(1) items with specific lookahead symbols. These lookaheads allow reductions to be applied according to the exact context of each item.

Compared with:

- **LR(0):** reductions may be placed across all terminal symbols.
- **SLR(1):** reductions are determined using FOLLOW sets.
- **CLR(1):** reductions are determined using the specific lookahead associated with each LR(1) item.

This additional contextual information helps reduce shift/reduce and reduce/reduce conflicts when working with more complex grammars.

For this reason, CLR(1) was selected in order to represent and analyze a larger and more realistic subset of C while still applying the theoretical parsing concepts studied in class.

The canonical collection will be constructed using LR(1) items, CLOSURE and GOTO operations.

## General Architecture

```text
C Source Code
      |
      v
Lexical Analyzer
      |
      v
Tokens
      |
      v
CLR(1) Parser
      |
      v
Parse Tree
      |
      v
Syntax-Directed Translation
      |
      v
Semantic Analysis
      |
      v
Result
```

## Implementation Language

Python 3

## Language Scope

The project will analyze a broad defined subset of the C programming language.

CLR(1) was selected to allow the grammar to cover more C language constructs than simpler LR parsing methods.

The exact supported constructs will be determined and documented according to the final CLR(1) grammar developed for the project.

## Team

**Team 07 - Compilers - Group 5 - UNAM**
