

from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler



# UI constants
CATEGORIES_PER_ROW = 3

def push_state(context: ContextTypes.DEFAULT_TYPE):
    if not 'stack' in context.user_data:
        context.user_data['stack'] = []
        context.user_data['set_previous'] = True
    if context.user_data['set_previous']:
        if len(context.user_data['stack']) != 0 and context.user_data['stack'][-1] == context.user_data['previous_state']:
            print("not pushing to stack cause same value on top")
            return
        if 'previous_state' in context.user_data and context.user_data['previous_state'] is not None:
            context.user_data['stack'].append(context.user_data['previous_state'])
            print("pushed to stack -> " + str(context.user_data['stack']))
    else:
        "stack not pushing cause go back"
        context.user_data['set_previous'] = True


def get_previous_state(context: ContextTypes.DEFAULT_TYPE):
    assert len(context.user_data['stack']) != 0
    state = context.user_data['stack'].pop()
    print("poped from stack -> " + str(context.user_data['stack']))
    return state
