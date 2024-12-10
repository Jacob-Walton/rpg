using System;
using System.Linq;
using System.Collections.Generic;

using RPG.Core;

namespace RPG.Commands
{
    /// <summary>
    /// Handles commands for the game.
    /// </summary>
    public class CommandHandler
    {
        private readonly Dictionary<string, ICommand> _commands = [];
        private Action<string> _inputHandler;
        private GameState? _currentState;

        /// <summary>
        /// Gets or sets the current input handler.
        /// </summary>
        public Action<string> InputHandler
        {
            get => _inputHandler;
            set => _inputHandler = value ?? DefaultInputHandler;
        }

        /// <summary>
        /// Initializes a new instance of the CommandHandler class.
        /// </summary>
        public CommandHandler()
        {
            _inputHandler = DefaultInputHandler;
        }

        /// <summary>
        /// The default input handler that processes commands.
        /// </summary>
        /// <param name="input">The input string to process.</param>
        private void DefaultInputHandler(string input)
        {
            if (string.IsNullOrWhiteSpace(input) || _currentState == null) return;

            string[] parts = input.Split(' ', 2);
            string commandName = parts[0].ToLower();
            string args = parts.Length > 1 ? parts[1] : string.Empty;

            if (_commands.TryGetValue(commandName, out ICommand? command))
            {
                try
                {
                    command.Execute(args, _currentState);
                }
                catch (Exception ex)
                {
                    _currentState.GameLog.Add(new ColoredText($"[Error] {ex.Message}", ConsoleColor.Red));
                }
            }
        }

        /// <summary>
        /// Registers a command with the command handler.
        /// </summary>
        /// <param name="command">The command to register.</param>
        public void RegisterCommand(ICommand command)
        {
            _commands[command.Name.ToLower()] = command;

            // Register aliases
            foreach (string alias in command.Aliases)
            {
                _commands[alias.ToLower()] = command;
            }
        }

        /// <summary>
        /// Processes the given input string using the current input handler.
        /// </summary>
        /// <param name="input">The input string to process.</param>
        public void ProcessInput(string input)
        {
            _inputHandler(input);
        }

        /// <summary>
        /// Executes a command with the given input and game state.
        /// </summary>
        /// <param name="input">The input string to parse and execute.</param>
        /// <param name="state">The current game state.</param>
        /// <returns>True if the command was executed successfully, otherwise false.</returns>
        public bool ExecuteCommand(string input, GameState state)
        {
            _currentState = state;

            string[] parts = input.Split(' ', 2);
            string commandName = parts[0].ToLower();
            string args = parts.Length > 1 ? parts[1] : string.Empty;

            if (_commands.TryGetValue(commandName, out ICommand? command))
            {
                try
                {
                    command.Execute(args, state);
                    return true;
                }
                catch (Exception ex)
                {
                    state.GameLog.Add(new ColoredText($"[Error] {ex.Message}", ConsoleColor.Red));
                    return false;
                }
            }

            return false;
        }

        /// <summary>
        /// Gets a list of all registered commands.
        /// </summary>
        /// <returns>A list of all registered commands.</returns>
        public IEnumerable<ICommand> GetCommands()
        {
            // create set of unique commands
            IEnumerable<ICommand> commands = _commands.Values.Distinct();

            return commands.Where(c => !string.IsNullOrEmpty(c.Name));
        }
    }
}