"""Background Task Management Module.

This module provides the BackgroundTaskManager class for handling asynchronous
BoardGameGeek API operations without blocking the user interface.

The manager handles:
- Background BGG API data fetching and expansion lookups
- Task cancellation and cleanup with centralized lifecycle management
- Thread management and coordination
- Callback coordination for UI updates
- Unified error handling and cancellation checking
- Common task initialization and cleanup patterns

Architecture:
    The module uses a shared helper method pattern to eliminate code duplication.
    Common operations like task cleanup, initialization, and error handling are
    centralized in private helper methods for maintainability.

Usage:
    background_manager = BackgroundTaskManager()
    background_manager.fetch_bgg_data_in_background("search_term", callback)
    background_manager.fetch_expansions_in_background(game_id, callback)
"""

import threading
import time
from models.game import Game


class BackgroundTaskManager:
    """Manages background tasks for fetching and updating game data.
    
    This class coordinates background operations for BoardGameGeek API interactions,
    ensuring the UI remains responsive while data is being fetched. It provides
    unified task lifecycle management, cancellation support, and callback coordination
    through centralized helper methods.
    
    Features:
        - Non-blocking BGG API operations (search and expansion fetch)
        - Unified task cancellation and cleanup via shared helpers
        - Centralized error handling and cancellation checking
        - Callback management for UI updates
        - Thread safety and coordination
        - Automatic task cleanup on completion
        - DRY principle implementation with shared task patterns
        
    Attributes:
        running_tasks (set): Set of currently active task IDs
        completed_callbacks (dict): Mapping of task IDs to completion callbacks
        cancelled_tasks (set): Set of task IDs that have been cancelled
        task_threads (dict): Mapping of task IDs to their thread objects
        
    Architecture:
        Uses private helper methods to eliminate code duplication:
        - _start_background_task(): Common task initialization
        - _execute_background_task(): Unified error handling and execution
        - _cleanup_task(): Centralized cleanup logic
        
    Thread Safety:
        This class is designed to be thread-safe for coordinating between
        the main UI thread and background worker threads.
    """
    
    def __init__(self):
        """Initialize the BackgroundTaskManager.
        
        Sets up the internal data structures for tracking active tasks,
        callbacks, and thread management.
        """
        self.running_tasks = set()
        self.completed_callbacks = {}
        self.cancelled_tasks = set()
        self.task_threads = {}
    
    def cancel_search_tasks(self):
        """Cancel all currently running BGG search tasks.
        
        Marks all search tasks (those with IDs starting with 'bgg_search_')
        for cancellation. The actual task threads will check this status
        and terminate gracefully.
        
        Note:
            This only affects search tasks, not expansion fetch tasks.
            Cancellation is cooperative - tasks must check their status.
        """
        search_tasks = [tid for tid in self.running_tasks if tid.startswith("bgg_search_")]
        for task_id in search_tasks:
            self.cancelled_tasks.add(task_id)
            print(f"🚫 Cancelled background task: {task_id}")
    
    def fetch_bgg_data_in_background(self, search_query, callback=None, immediate_callback=None):
        """Fetch BGG data in the background without blocking the UI.
        
        Starts a background thread to search BoardGameGeek API and fetch
        detailed game information. Cancels any existing search tasks first.
        Uses centralized task management helpers for consistent behavior.
        
        Args:
            search_query (str): The search term to look up on BGG (name or ID)
            callback (callable, optional): Function to call when search completes
                with detailed results. Called with list of Game objects.
            immediate_callback (callable, optional): Function to call immediately
                with basic search results. Called with list of Game objects.
                
        Process:
            1. Cancel any existing search tasks
            2. Generate unique task ID
            3. Use _start_background_task() for consistent initialization
            4. Background thread uses _execute_background_task() for unified handling
            5. Callbacks are invoked with results
            6. Cleanup happens automatically via _cleanup_task()
            
        Note:
            The search_query can be either a game name or BGG ID.
            The Game.search_bgg_api() method handles the distinction.
        """
        # Cancel any existing search tasks
        self.cancel_search_tasks()
        
        task_id = f"bgg_search_{search_query}_{int(time.time())}"
        
        if task_id not in self.running_tasks:
            self._start_background_task(
                task_id, 
                callback, 
                self._background_bgg_fetch, 
                (search_query, task_id, immediate_callback),
                f"🔄 Started background BGG fetch for '{search_query}'"
            )
    
    def _background_bgg_fetch(self, search_query, task_id, immediate_callback=None):
        """Background worker function to fetch BGG data.
        
        This method runs in a separate thread and performs the actual BGG API
        calls. It includes cancellation checking and proper error handling.
        
        Args:
            search_query (str): The search term to look up on BGG
            task_id (str): Unique identifier for this task
            immediate_callback (callable, optional): Callback for immediate results
        """
        def work_function():
            print(f"🌐 Background: Fetching BGG data for '{search_query}'...")
            games = Game.search_bgg_api(
                search_query, 
                cancellation_checker=lambda: task_id in self.cancelled_tasks,
                immediate_callback=immediate_callback
            )
            print(f"✅ Background: Completed BGG fetch for '{search_query}' - found {len(games)} games")
            return games
        
        def error_message(e):
            return f"❌ Background BGG fetch error for '{search_query}': {e}"
        
        self._execute_background_task(task_id, work_function, error_message)
    
    def fetch_expansions_in_background(self, base_game_id, callback=None):
        """Fetch game expansions in the background.
        
        Starts a background thread to fetch expansions for a specific base game
        from BoardGameGeek API without blocking the UI. Uses centralized task
        management helpers for consistent behavior.
        
        Args:
            base_game_id (int): BGG ID of the base game to find expansions for
            callback (callable, optional): Function to call when fetch completes.
                Called with list of Game objects representing expansions.
                
        Process:
            1. Generate unique task ID for this expansion fetch
            2. Use _start_background_task() for consistent initialization
            3. Background thread uses _execute_background_task() for unified handling
            4. Callback is invoked with expansion list
            5. Cleanup happens automatically via _cleanup_task()
            
        Note:
            Expansion searches can run concurrently with game searches.
            Each has independent cancellation and lifecycle management.
        """
        task_id = f"expansions_{base_game_id}_{int(time.time())}"
        
        if task_id not in self.running_tasks:
            self._start_background_task(
                task_id,
                callback,
                self._background_expansion_fetch,
                (base_game_id, task_id),
                f"🔄 Started background expansion fetch for game {base_game_id}"
            )
    
    def _background_expansion_fetch(self, base_game_id, task_id):
        """Background worker function to fetch expansion data.
        
        This method runs in a separate thread and fetches expansion information
        for a base game from the BGG API.
        
        Args:
            base_game_id (int): BGG ID of the base game
            task_id (str): Unique identifier for this task
        """
        def work_function():
            print(f"🌐 Background: Fetching expansions for game {base_game_id}...")
            expansions = Game.get_bgg_expansions(
                base_game_id, 
                cancellation_checker=lambda: task_id in self.cancelled_tasks
            )
            print(f"✅ Background: Completed expansion fetch for game {base_game_id} - found {len(expansions)} expansions")
            return expansions
        
        def error_message(e):
            return f"❌ Background expansion fetch error for game {base_game_id}: {e}"
        
        self._execute_background_task(task_id, work_function, error_message)
    
    def is_busy(self):
        """Check if any background tasks are running."""
        return len(self.running_tasks) > 0
    
    def get_running_tasks(self):
        """Get list of currently running task IDs."""
        return list(self.running_tasks)
    
    def _cleanup_task(self, task_id):
        """Clean up task tracking data for a completed or cancelled task.
        
        Removes the task from all internal tracking structures to prevent
        memory leaks and ensure proper task lifecycle management.
        
        Args:
            task_id (str): The task ID to clean up
            
        Cleanup Operations:
            - Remove from running_tasks set
            - Delete completion callback mapping
            - Remove from cancelled_tasks set
            - Delete thread reference
        """
        if task_id in self.running_tasks:
            self.running_tasks.remove(task_id)
        if task_id in self.completed_callbacks:
            del self.completed_callbacks[task_id]
        if task_id in self.cancelled_tasks:
            self.cancelled_tasks.remove(task_id)
        if task_id in self.task_threads:
            del self.task_threads[task_id]
    
    def _start_background_task(self, task_id, callback, target_function, args, start_message):
        """Start a new background task with common initialization logic.
        
        Centralizes the task startup process to ensure consistent behavior
        across all background operations. Handles thread creation, callback
        registration, and task tracking.
        
        Args:
            task_id (str): Unique identifier for the task
            callback (callable): Function to call when task completes
            target_function (callable): Function to run in background thread
            args (tuple): Arguments to pass to target_function
            start_message (str): Message to print when task starts
            
        Process:
            1. Add task to running_tasks tracking
            2. Register completion callback if provided
            3. Create daemon thread with target function
            4. Store thread reference for management
            5. Start thread execution
            6. Print status message
        """
        self.running_tasks.add(task_id)
        if callback:
            self.completed_callbacks[task_id] = callback
        
        thread = threading.Thread(
            target=target_function,
            args=args,
            daemon=True
        )
        self.task_threads[task_id] = thread
        thread.start()
        print(start_message)
    
    def _execute_background_task(self, task_id, work_function, error_message_func):
        """Execute a background task with unified error handling and cancellation logic.
        
        Provides centralized execution framework for all background tasks,
        ensuring consistent cancellation checking, error handling, callback
        invocation, and cleanup across all task types.
        
        Args:
            task_id (str): Unique identifier for this task
            work_function (callable): Function that performs the actual work and returns results.
                This function should handle its own cancellation checking during long operations.
            error_message_func (callable): Function that takes an exception and returns error message string
            
        Execution Flow:
            1. Check for pre-execution cancellation
            2. Execute work_function and capture results
            3. Check for mid-execution cancellation
            4. Invoke completion callback with results if not cancelled
            5. Handle and log any exceptions that occur
            6. Ensure cleanup happens regardless of success/failure
            
        Cancellation Behavior:
            Tasks can be cancelled at two points: before execution starts
            and after execution completes. The work_function itself is
            responsible for checking cancellation during long operations.
        """
        try:
            # Check if task was cancelled before starting
            if task_id in self.cancelled_tasks:
                print(f"⏹️ Background task cancelled before start: {task_id}")
                return
            
            # Execute the work function
            result = work_function()
            
            # Check if task was cancelled during execution
            if task_id in self.cancelled_tasks:
                print(f"⏹️ Background task cancelled during execution: {task_id}")
                return
            
            # Call completion callback if provided and task wasn't cancelled
            if task_id in self.completed_callbacks and task_id not in self.cancelled_tasks:
                callback = self.completed_callbacks[task_id]
                if callback:
                    callback(result)
                
        except Exception as e:
            if task_id not in self.cancelled_tasks:
                print(error_message_func(e))
        
        finally:
            self._cleanup_task(task_id)


# Global instance
background_manager = BackgroundTaskManager()