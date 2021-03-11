"""
Austin Wong
001355444
2/22/2021
"""

# IMPORTS

# Custom packages
from dbinter import attempt_login, set_current_user
from model import *

# GUI
import seaborn as sns
import PySimpleGUI as sg
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib
matplotlib.use("TkAgg")


# CONSTANTS
# Heart rate values for input validation
MIN_HR = 0
MAX_HR = 500

# Fetal Health Status dictionary
fhs_dict = {
    1.0: 'Normal',
    2.0: 'Suspect',
    3.0: 'Pathologic'
}

# Inverse direction of Fetal Health Status dictionary
iv_fhs_dict = {v: k for k, v in fhs_dict.items()}

# Color-coding for Fetal Health Status
fhs_color = {
    1.0: 'yellowgreen',
    2.0: 'gold',
    3.0: 'firebrick'
}

# Ordered column names for database features
cols = ['baseline_value', 'accelerations', 'fetal_movement',
        'uterine_contractions', 'light_decelerations', 'severe_decelerations',
        'prolongued_decelerations', 'abnormal_short_term_variability',
        'mean_value_of_short_term_variability',
        'percentage_of_time_with_abnormal_long_term_variability',
        'mean_value_of_long_term_variability', 'histogram_width',
        'histogram_min', 'histogram_max', 'histogram_number_of_peaks',
        'histogram_number_of_zeroes', 'histogram_mode', 'histogram_mean',
        'histogram_median', 'histogram_variance', 'histogram_tendency']


def controller(conn):
    """
    Controls flow of GUI
    :param conn: Connection object to SQLite Database
    :return: None
    """

    # Don't start program if files were moved
    if conn is None:
        create_alert('Could not locate database file. Contact administrator.', 'Error', 'salmon')
        return

    sg.theme('LightBlue3')

    # Start at login screen
    event, values = create_login(conn)

    # Evaluate GUI events and move to next appropriate window
    while True:
        if event == 'Login' or event == '-Save Model-' or event == '-Save DB-' or event == '-Cancel-':
            event, values = create_menu()
        elif event == 'FETAL HEALTH STATUS':
            event, values = create_fhs()
        elif event == 'DASHBOARD':
            event, values = create_dashboard()
        elif event == 'TRAIN MODEL':
            event, values = create_train()
        elif event == "LOG OUT":
            event, values = create_login(conn)
        elif event in ('Exit', sg.WIN_CLOSED):
            break


# HELPER WINDOW FUNCTIONS
def draw_figure(canvas, figure):
    """
    Draws figure on Canvas object
    :param canvas: Canvas object
    :param figure: Figure object
    :return: Canvas object with figure added
    """
    figure_canvas_agg = FigureCanvasTkAgg(figure, canvas)
    figure_canvas_agg.draw()
    figure_canvas_agg.get_tk_widget().pack(side="top",
                                           fill="both",
                                           expand=1)
    return figure_canvas_agg


def create_window(columns, title='', calculate=False, cancel=False, save=False, error_msg=False, combo_list=[]):
    """
    Creates a window that adjusts with expansion and contraction
    :param columns: List of Column objects to use in center of window
    :param title: String for window title
    :param calculate: Set True to include "Calculate" button
    :param cancel: Set True to include "Cancel" button
    :param save: Set True to include "Save" button
    :param error_msg: Set True to include Text object for error messages
    :param combo_list: List of values for a ComboBox
    :return: layout of window (list) and finalized Window object
    """

    # Sandwich columns in between expanding left and right sections
    row = [sg.Text('', pad=(0, 0), key='-EXPAND_L-')]
    for column in columns:
        row.append(column)
    row.append(sg.Text('', pad=(0, 0), key='-EXPAND_R-'))

    # Create layout as follows:
    #    Expanding top section
    #    ComboBox (optional)
    #          CONTENT
    #    Error Message (optional)
    #    Buttons (optional)
    #    Expanding bottom section
    layout = [[sg.Text(key='-EXPAND_T-', font='ANY 1', pad=(0, 0))],
              [sg.Combo(values=combo_list,
                        visible=True if len(combo_list) >= 1 else False,
                        default_value=combo_list[0] if len(combo_list) >= 1 else '',
                        key='-GRAPH_COMBO-',
                        enable_events=True)],
              row,
              [sg.Text('', visible=error_msg, key='-Error Msg-', size=(50, 1))],
              [sg.B('Calculate', visible=calculate, key='-Calculate-'),
               sg.B('Save to Database', visible=save, key='-Save DB-'),
               sg.B('Cancel', visible=cancel, key='-Cancel-')],
              [sg.Text(key='-EXPAND_B-', font='ANY 1', pad=(0, 0))]
              ]

    # Create Window object
    window = sg.Window(title=title,
                       layout=layout,
                       resizable=True,
                       element_justification='c',
                       finalize=True
                       )

    # Apply expansion rules to each section
    for num in range(len(columns)):
        key = '-COLUMN'+str(num+1)+'-'
        window[key].expand(False, True, True)
    window['-EXPAND_T-'].expand(True, True, True)
    window['-EXPAND_L-'].expand(True, False, True)
    window['-EXPAND_R-'].expand(True, False, True)
    window['-EXPAND_B-'].expand(True, True, True)

    return layout, window


def create_alert(text, title, color):
    """
    Creates a popup alert
    :param text: String to display to user
    :param title: String for popup window title
    :param color: Color of text
    :return: None
    """
    layout = [[sg.Text(text, text_color=color)],
              [sg.B('OK')]
              ]

    window = sg.Window(title=title,
                       layout=layout,
                       element_justification='c',
                       finalize=True
                       )

    while True:
        event, values = window.read()
        if event == 'OK' or event == sg.WIN_CLOSED:
            window.close()
            break


def create_confirmation(fetal_data):
    """
    Creates a confirmation window for entering current patient's fetal health data into database
    :param fetal_data: List with values for current patient's fetal health attributes in order
    :return: 1 if data was successfully saved to database, 0 otherwise
    """
    layout = [[sg.Text('Enter ACTUAL fetal health status', text_color='black')],
              [sg.Combo(values=['Normal', 'Suspect', 'Pathologic'],
                        default_value='',
                        key='-FHS_COMBO-',
                        enable_events=True)],
              [sg.B('Save'), sg.B('Cancel')]
              ]

    window = sg.Window(title='Save Entry to Database',
                       layout=layout,
                       element_justification='c',
                       finalize=True
                       )

    while True:
        event, values = window.read()

        # Don't save
        if event == 'Cancel' or event == sg.WIN_CLOSED:
            window.close()
            return 0

        # Save
        elif event == 'Save':

            # Check that ACTUAL fetal health status is selected (make sure we're not saving incorrect predictions)
            if len(values['-FHS_COMBO-']) > 0:
                # Add fetal health status to end of list of patient data
                fetal_data.append(iv_fhs_dict[values['-FHS_COMBO-']])

                # Save to database
                if insert_fetal_data(fetal_data) == 1:
                    window.close()
                    create_alert('Entry saved to database', 'Success', 'black')
                    return 1
                # Error handling
                else:
                    create_alert('Unable to save entry to database. Try again later or contact your administrator.',
                                 'Error', 'red')
            # Nudge user to select fetal health status before saving
            else:
                create_alert('Select fetal health status', 'Error', 'red')


def check_inputs(window, values):
    """
    Validate fetal health data input
    :param window: Window object
    :param values: Dictionary with GUI element key-value pairs
    :return: 0 if there are no input errors, 1 if input errors were found
    """

    # Split fields into data types
    int_values = ['baseline_value', 'abnormal_short_term_variability',
                  'percentage_of_time_with_abnormal_long_term_variability',
                  'histogram_width', 'histogram_min', 'histogram_max',
                  'histogram_number_of_peaks', 'histogram_number_of_zeroes',
                  'histogram_mode', 'histogram_median', 'histogram_variance',
                  'histogram_mean', 'histogram_tendency'
                  ]
    float_values = ['accelerations', 'fetal_movement', 'uterine_contractions',
                    'light_decelerations', 'severe_decelerations', 'prolongued_decelerations',
                    'mean_value_of_short_term_variability', 'mean_value_of_long_term_variability',
                    ]

    # Check if inputs are correct data type
    try:
        for value in int_values:
            values[value] = int(values[value])
            window[value].update(background_color='White')
    except ValueError:
        for value in int_values:
            window[value].update(background_color='Orange')
        return 1, 'Highlighted input must be integers'
    try:
        for value in float_values:
            values[value] = float(values[value])
            window[value].update(background_color='White')
    except ValueError:
        for value in float_values:
            window[value].update(background_color='Orange')
        return 1, 'Highlighted input must be numeric.'

    # Check if input is within acceptable range for each attribute
    if not (MIN_HR <= values['baseline_value'] <= MAX_HR):
        return 1, 'Baseline FHR must be between {} and {}'.format(MIN_HR, MAX_HR)
    elif not (0 <= values['accelerations'] <= 1):
        return 1, 'Accelerations must be between 0 and 1'
    elif not (0 <= values['fetal_movement'] <= 1):
        return 1, 'Fetal Movement must be between 0 and 1'
    elif not (0 <= values['uterine_contractions'] <= 1):
        return 1, 'Uterine Contractions must be between 0 and 1'
    elif not (0 <= values['light_decelerations'] <= 1):
        return 1, 'Light Decelerations must be between 0 and 1'
    elif not (0 <= values['severe_decelerations'] <= 1):
        return 1, 'Severe Decelerations must be between 0 and 1'
    elif not (0 <= values['prolongued_decelerations'] <= 1):
        return 1, 'Prolongued Decelerations must be between 0 and 1'
    elif not (0 <= values['abnormal_short_term_variability'] <= 100):
        return 1, 'Abnormal Short Term Variability must be between 0 and 100'
    elif not (0 <= values['mean_value_of_short_term_variability'] <= 100):
        return 1, 'Mean Value of Short Term Variability must be between 0 and 100'
    elif not (0 <= values['percentage_of_time_with_abnormal_long_term_variability'] <= 100):
        return 1, 'Percentage of Time with Abnormal Long Term Variability must be between 0 and 100'
    elif not (0 <= values['mean_value_of_long_term_variability'] <= 100):
        return 1, 'Mean Value of Long Term Variability must be between 0 and 100'
    elif not (MIN_HR <= values['histogram_width'] <= MAX_HR):
        return 1, 'Histogram Width must be between {} and {}'.format(MIN_HR, MAX_HR)
    elif not (MIN_HR <= values['histogram_min'] <= MAX_HR):
        return 1, 'Histogram Min must be between {} and {}'.format(MIN_HR, MAX_HR)
    elif not (MIN_HR <= values['histogram_max'] <= MAX_HR):
        return 1, 'Histogram Max must be between {} and {}'.format(MIN_HR, MAX_HR)
    elif not (0 <= values['histogram_number_of_peaks'] <= 50):
        return 1, 'Histogram Number of Peaks must be between 0 and 50'
    elif not (0 <= values['histogram_number_of_zeroes'] <= 50):
        return 1, 'Histogram Number of Zeroes must be between 0 and 50'
    elif not (MIN_HR <= values['histogram_mode'] <= MAX_HR):
        return 1, 'Histogram Mode must be between {} and {}'.format(MIN_HR, MAX_HR)
    elif not (MIN_HR <= values['histogram_mean'] <= MAX_HR):
        return 1, 'Histogram Mean must be between {} and {}'.format(MIN_HR, MAX_HR)
    elif not (MIN_HR <= values['histogram_median'] <= MAX_HR):
        return 1, 'Histogram Median must be between {} and {}'.format(MIN_HR, MAX_HR)
    elif not (MIN_HR <= values['histogram_variance'] <= MAX_HR):
        return 1, 'Histogram Variance must be between {} and {}'.format(MIN_HR, MAX_HR)
    elif not (values['histogram_tendency'] in (-1, 0, 1)):
        return 1, 'Histogram Tendency must be -1, 0, or 1'

    return 0, 'Success'


# MAIN SCREENS
def create_login(conn):
    """
    Creates a login screen
    :param conn: Connection object to SQLite DB
    :return: event (string for what happened on the screen),
             values (dictionary with GUI element values at time of event)
    """

    column1 = [[sg.T('Username:'), sg.In(key='-ID-')],
               [sg.T('Password:'), sg.In(key='-Password-', password_char='*')],
               [sg.B('Login'), sg.B('Exit')],
               [sg.T('Incorrect username or password', key='-Error-', text_color='Red', visible=False)]]

    columns = [sg.Column(column1,
                         vertical_alignment='center',
                         justification='center',
                         element_justification='center',
                         k='-COLUMN1-')]

    layout, window = create_window(columns, 'LOGIN')

    while True:
        event, values = window.read()

        if event == 'Login':
            # Successful login
            if attempt_login(values['-ID-'], values['-Password-'], conn) == 1:

                # Load our data
                load_fetal_data(conn)
                load_model()

                # Update current_user, and log event to User Log
                set_current_user(values['-ID-'])
                dirname = Path(__file__).parent.absolute()
                user_filepath = Path(dirname, 'user_log').with_suffix('.txt')
                f = open(user_filepath, 'a')
                f.write('{} logged in at {}\n'.format(values['-ID-'], datetime.datetime.now()))
                f.close()

                values['-Password-'] = None
                window.close()
                return event, values
            # Unsuccessful login
            else:
                window['-Error-'].update(visible=True)

        elif event == "Exit" or event == sg.WIN_CLOSED:
            window.close()
            return event, values


def create_menu():
    """
    Creates a menu screen
    :return: event (string for what happened on the screen),
             values (dictionary with GUI element values at time of event)
    """

    menu_items = ['FETAL HEALTH STATUS',
                  'DASHBOARD',
                  'TRAIN MODEL',
                  'LOG OUT']
    column1 = []

    # Create buttons for each option
    for item in menu_items:
        column1.append([sg.B(item)])

    columns = [sg.Column(column1,
                         vertical_alignment='center',
                         justification='center',
                         element_justification='center',
                         k='-COLUMN1-')]

    layout, window = create_window(columns, 'MENU')

    while True:
        event, values = window.read()
        if event in menu_items or event == sg.WIN_CLOSED:
            window.close()
            return event, values


def create_fhs():
    """
    Create screen for:
       • inputting fetal health data,
       • predicting fetal health status (FHS),
       • and saving fetal health data to database
    :return: event (string for what happened on the screen),
             values (dictionary with GUI element values at time of event)
    """

    column1 = [[sg.Text('Baseline FHR')],
               [sg.Text('Accelerations')],
               [sg.Text('Fetal Movement')],
               [sg.Text('Uterine Contractions')],
               [sg.Text('Light Decelerations')],
               [sg.Text('Severe Decelerations')],
               [sg.Text('Prolongued Decelerations')],
               [sg.Text('Abnormal Short Term Variability')],
               [sg.Text('Mean Value of Short Term Variability')],
               [sg.Text('% of Time with Abnormal Long Term Variability')],
               [sg.Text('Mean Value of Long Term Variability')],
               ]

    column2 = [[sg.In(key='baseline_value')],
               [sg.In(key='accelerations')],
               [sg.In(key='fetal_movement')],
               [sg.In(key='uterine_contractions')],
               [sg.In(key='light_decelerations')],
               [sg.In(key='severe_decelerations')],
               [sg.In(key='prolongued_decelerations')],
               [sg.In(key='abnormal_short_term_variability')],
               [sg.In(key='mean_value_of_short_term_variability')],
               [sg.In(key='percentage_of_time_with_abnormal_long_term_variability')],
               [sg.In(key='mean_value_of_long_term_variability')]
               ]

    column3 = [[sg.Text('Histogram Width')],
               [sg.Text('Histogram Min')],
               [sg.Text('Histogram Max')],
               [sg.Text('Histogram # of Peaks')],
               [sg.Text('Histogram # of Zeroes')],
               [sg.Text('Histogram Mode')],
               [sg.Text('Histogram Mean')],
               [sg.Text('Histogram Median')],
               [sg.Text('Histogram Variance')],
               [sg.Text('Histogram Tendency')]
               ]

    column4 = [[sg.In(key='histogram_width')],
               [sg.In(key='histogram_min')],
               [sg.In(key='histogram_max')],
               [sg.In(key='histogram_number_of_peaks')],
               [sg.In(key='histogram_number_of_zeroes')],
               [sg.In(key='histogram_mode')],
               [sg.In(key='histogram_mean')],
               [sg.In(key='histogram_median')],
               [sg.In(key='histogram_variance')],
               [sg.In(key='histogram_tendency')]
               ]

    column_els = [column1, column2, column3, column4]
    columns = []
    for ind in range(len(column_els)):
        key = '-COLUMN'+str(ind+1)+'-'
        columns.append(sg.Column(column_els[ind],
                                 vertical_alignment='center',
                                 element_justification='right',
                                 justification='right',
                                 k=key
                                 ))

    layout, window = create_window(columns, 'FETAL HEALTH STATUS', calculate=True, cancel=True, save=True)

    # Pre-populate fields if the user was previously at this screen
    if get_current_patient() is not None:
        auto_populate = get_current_patient()
        for key, value in auto_populate.items():
            window[key].update(value=value)

    fhs = None
    while True:
        event, values = window.read()

        if event in ('-Cancel-', sg.WIN_CLOSED):
            window.close()
            return event, values

        # Calculate Button was pressed; Predict FHS
        elif event == '-Calculate-':

            # Validate input
            error, error_msg = check_inputs(window, values)

            # Input is Valid
            if error == 0:

                # Put data into correct format
                new_df = pd.DataFrame(columns=cols)
                new_data = {}
                for col in cols:
                    new_data[col] = values[col]
                set_current_patient(new_data)
                new_df = new_df.append(new_data, ignore_index=True)

                # Make Prediction
                y_preds = get_model().predict(new_df)
                fhs = y_preds[0]

                # Display Prediction to user
                msg = 'Predicted Fetal Health Status is ' + str(fhs_dict[fhs]).upper()
                window['-Error Msg-'].update(value=msg, visible=True, text_color='Black')

                # Color Code Prediction
                if fhs == 3.0:
                    window['-Error Msg-'].update(background_color='Red')
                    create_alert('Patient\'s Status is Pathologic', 'Alert', 'red')
                elif fhs == 2.0:
                    window['-Error Msg-'].update(background_color='Yellow')
                elif fhs == 1.0:
                    window['-Error Msg-'].update(background_color='Green')

            # Input Error Detected, Show Error Msg
            elif error == 1:
                window['-Error Msg-'].update(value=error_msg, visible=True, text_color='Red')

        # Save Database Button was Pressed
        elif event == '-Save DB-':

            # Validate input
            error, error_msg = check_inputs(window, values)

            # Confirm user wants to save
            if error == 0:

                # Save data to current_patient variable
                new_data = {}
                new_data_list = []
                for col in cols:
                    new_data[col] = values[col]
                    new_data_list.append(values[col])
                set_current_patient(new_data)

                # Saved Successfully to database (errors handled in create_confirmation())
                if create_confirmation(new_data_list) == 1:
                    window.close()
                    return event, values

            # Input is invalid, display error message
            elif error == 1:
                window['-Error Msg-'].update(value=error_msg, visible=True, text_color='Red')


def create_dashboard():
    """
    Creates a dashboard for users to analyze the data in the database
    :return: event (string for what happened on the screen),
             values (dictionary with GUI element values at time of event)
    """

    df = Model.fetal_data

    # Organize Layout into a 2x2 grid (4 total graphs)
    column1 = [[sg.Canvas(key="-CANVAS (0, 0)-")],
               [sg.Canvas(key="-CANVAS (1, 0)-")]
               ]
    column2 = [[sg.Canvas(key="-CANVAS (0, 1)-")],
               [sg.Canvas(key="-CANVAS (1, 1)-")]]
    column_els = [column1, column2]
    columns = []
    for ind in range(len(column_els)):
        key = '-COLUMN'+str(ind+1)+'-'
        columns.append(sg.Column(column_els[ind],
                                 vertical_alignment='center',
                                 element_justification='right',
                                 justification='right',
                                 k=key
                                 ))

    # Create ComboBox options for graphs to choose from
    combo_list = ['Overview', 'Normal Status', 'Suspect Status', 'Pathologic Status', 'Accelerations', 'Baseline FHR',
                  'Prolongued Decelerations', 'Correlation Matrix']

    # Create Window
    layout, window = create_window(columns, 'DASHBOARD', cancel=True, combo_list=combo_list)

    # Maximize the window for optimal viewing
    window.maximize()

    # Plot initial overview graphs
    canvases = plot_all_graphs(window, df)

    # Respond to user interaction
    while True:
        event, values = window.read()

        if event in ('-Cancel-', sg.WIN_CLOSED):
            window.close()
            return event, values

        # User chose new graph from ComboBox
        elif event == '-GRAPH_COMBO-':

            # Clear the canvases
            for canvas in canvases:
                canvas.get_tk_widget().forget()
                plt.close('all')

            # Display Overview Graphs
            if values['-GRAPH_COMBO-'] == 'Overview':
                canvases = plot_all_graphs(window, df)

            # Display Normal FHS Graphs
            elif values['-GRAPH_COMBO-'] == 'Normal Status':
                normal_df = df[df["fetal_health"] == 1.0]
                canvases = plot_all_graphs(window, normal_df)

            # Display Suspect FHS Graphs
            elif values['-GRAPH_COMBO-'] == 'Suspect Status':
                suspect_df = df[df["fetal_health"] == 2.0]
                canvases = plot_all_graphs(window, suspect_df)

            # Display Pathologic FHS Graphs
            elif values['-GRAPH_COMBO-'] == 'Pathologic Status':
                path_df = df[df["fetal_health"] == 3.0]
                canvases = plot_all_graphs(window, path_df)

            # Display Accelerations Graphs
            elif values['-GRAPH_COMBO-'] == 'Accelerations':
                canvases = plot_all_accelerations(window)

            # Display Baseline FHR Graphs
            elif values['-GRAPH_COMBO-'] == 'Baseline FHR':
                canvases = plot_all_baseline_fhr(window)

            # Display Prolongued Decelerations Graphs
            elif values['-GRAPH_COMBO-'] == 'Prolongued Decelerations':
                canvases = plot_all_prolongued_decelerations(window)

            # Display Correlation Matrix (new window)
            elif values['-GRAPH_COMBO-'] == 'Correlation Matrix':
                plot_correlation_matrix(df)


def create_train():
    """
    Creates a window for retraining a machine learning model on the database data
    :return: event (string for what happened on the screen),
             values (dictionary with GUI element values at time of event)
    """

    column1 = [[sg.Text('Training a model may take several minutes', k='-IN PROGRESS-')],
               [sg.Multiline('', key='-REPORT-', visible=False, size=(60, 20))],
               [sg.B('SAVE', k='-Save Model-'), sg.B('TRAIN', k='-Train-'), sg.B('CANCEL', k='-Cancel-')]
               ]
    columns = [sg.Column(column1,
                         vertical_alignment='center',
                         element_justification='right',
                         justification='right',
                         k='-COLUMN1-')
               ]
    layout, window = create_window(columns, 'TRAIN MODEL')

    model = None
    while True:
        event, values = window.read()

        if event in ('-Cancel-', sg.WIN_CLOSED):
            window.close()
            return event, values

        # Train button was pressed
        elif event == '-Train-':
            window['-IN PROGRESS-'].update(value='Training Model...')
            model, report = train_model()

            # Display Report on model performance
            report_df = pd.DataFrame(report)
            window['-REPORT-'].update(value=str(report_df.T), visible=True)
            window['-IN PROGRESS-'].update(value='Complete')
            plt.show()

        # Save button was pressed
        elif event == '-Save Model-':
            if model is not None:
                save_model(model)
                create_alert('Model saved', 'Success', 'black')
                window.close()
                return event, values
            else:
                create_alert('You must train a new model before saving', 'Error', 'black')

# PLOT FUNCTIONS


def plot_graphs_helper(window, fig1, fig2, fig3, fig4):
    """
    Plots 4 figures onto canvases in a 2x2 grid
    :param window: Window object to plot graphs on
    :param fig1: Upper left figure
    :param fig2: Upper right figure
    :param fig3: Bottom left figure
    :param fig4: Bottom right figure
    :return: Canvas objects for each figure
    """

    # Create Graphs
    canvas1 = draw_figure(window["-CANVAS (0, 0)-"].TKCanvas, fig1)
    canvas2 = draw_figure(window["-CANVAS (0, 1)-"].TKCanvas, fig2)
    canvas3 = draw_figure(window["-CANVAS (1, 0)-"].TKCanvas, fig3)
    canvas4 = draw_figure(window["-CANVAS (1, 1)-"].TKCanvas, fig4)

    return canvas1, canvas2, canvas3, canvas4


def plot_fhs_overview(df):
    """
    Plots figure of patients split by fetal health status
    :param df: Pandas DataFrame with fetal health data to be plotted
    :return: Figure object
    """

    # Get all data and convert to percentages
    all_df = Model.fetal_data
    x = all_df["fetal_health"].value_counts(normalize=True).index.to_list()
    y = [100 * all_df["fetal_health"].value_counts(normalize=True)[i] for i in x]

    # Standard colors and labels
    xlabels = [fhs_dict[i] for i in x]
    xcolors = [fhs_color[i] for i in x]
    y_pos = np.arange(len(xlabels))

    # Change all but one bar color to gray if we're focusing on one
    focal_statuses = df["fetal_health"].value_counts(normalize=True).index.to_list()
    if len(focal_statuses) == 1:
        xcolors = [fhs_color[i] if i == focal_statuses[0] else 'gray' for i in x]

    # Create bar graph and format
    fig, ax = plt.subplots()
    ax = plt.bar(y_pos, y, color=xcolors)
    plt.xticks(y_pos, xlabels)
    plt.ylabel('% of Patients')
    plt.tick_params(labelbottom='off')
    plt.title('Percent of Patients by Fetal Health Status')

    return fig


def plot_accelerations(df):
    """
    Plots Accelerations data
    :param df: Pandas DataFrame with fetal health data to be plotted
    :return: Figure object
    """

    fig, ax = plt.subplots()

    # Determine Title and Color based on FHS
    color = '#1f77b4'
    statuses = df['fetal_health'].value_counts().index.to_list()
    if len(statuses) > 1:
        ax.set_title('Accelerations for All Statuses')
    else:
        ax.set_title('Accelerations for ' + fhs_dict[statuses[0]] + ' Status')
        color = fhs_color[statuses[0]]

    # Standard formatting
    ax = df['accelerations'].hist(bins=np.arange(0, 0.0105, 0.0005),
                                  color=color)
    ax.set_xlabel('Accelerations')
    ax.set_ylabel('# of Patients')

    return fig


def plot_baseline_fhr(df):
    """
    Plots Baseline Fetal Heart Rate histogram
    :param df: Pandas DataFrame with fetal health data
    :return: Figure object
    """
    fig, ax = plt.subplots()

    # Determine Title and Color
    color = '#1f77b4'
    statuses = df['fetal_health'].value_counts().index.to_list()
    if len(statuses) > 1:
        ax.set_title('Baseline Fetal Heart Rate for All Statuses')
    else:
        ax.set_title('Baseline Fetal Heart Rate for ' + fhs_dict[statuses[0]] + ' Status')
        color = fhs_color[statuses[0]]

    # Standard formatting
    ax = df.baseline_value.hist(bins=np.arange(100, 180, 10),
                                color=color)
    ax.set_xlabel('Baseline Fetal Heart Rate')
    ax.set_ylabel('# of Patients')

    return fig


def plot_prolongued_decelerations(df):
    """
    Plots Prolongued Decelerations histogram
    :param df: Pandas DataFrame with fetal health data
    :return:
    """
    fig, ax = plt.subplots()

    # Determine Title and Color
    color = '#1f77b4'
    statuses = df['fetal_health'].value_counts().index.to_list()
    if len(statuses) > 1:
        ax.set_title('Prolongued Decelerations for All Statuses')
    else:
        ax.set_title('Prolongued Decelerations for ' + fhs_dict[statuses[0]] + ' Status')
        color = fhs_color[statuses[0]]

    # Standard formatting
    ax = df['prolongued_decelerations'].hist(bins=np.arange(0, 0.0065, 0.001),
                                             color=color)
    ax.set_xlabel('Prolongued Decelerations')
    ax.set_ylabel('# of Patients')

    return fig


def plot_all_accelerations(window):
    """
    Plots Accelerations graphs for each FHS category and combined
    :param window: Window object to use for plotting
    :return: Canvas objects with figures plotted onto each canvas
    """

    all_df = Model.fetal_data
    fig1 = plot_accelerations(all_df)
    fig2 = plot_accelerations(all_df[all_df['fetal_health'] == 1.0])
    fig3 = plot_accelerations(all_df[all_df['fetal_health'] == 2.0])
    fig4 = plot_accelerations(all_df[all_df['fetal_health'] == 3.0])

    return plot_graphs_helper(window, fig1, fig2, fig3, fig4)


def plot_all_baseline_fhr(window):
    """
    Plots Baseline Fetal Heart Rate graphs for each FHS category and combined
    :param window: Window object to use for plotting
    :return: Canvas objects with figures plotted onto each canvas
    """
    all_df = Model.fetal_data
    fig1 = plot_baseline_fhr(all_df)
    fig2 = plot_baseline_fhr(all_df[all_df['fetal_health'] == 1.0])
    fig3 = plot_baseline_fhr(all_df[all_df['fetal_health'] == 2.0])
    fig4 = plot_baseline_fhr(all_df[all_df['fetal_health'] == 3.0])

    return plot_graphs_helper(window, fig1, fig2, fig3, fig4)


def plot_all_prolongued_decelerations(window):
    """
    Plots Prolongued Decelerations graphs for each FHS category and combined
    :param window: Window object to use for plotting
    :return: Canvas objects with figures plotted onto each canvas
    """
    all_df = Model.fetal_data
    fig1 = plot_prolongued_decelerations(all_df)
    fig2 = plot_prolongued_decelerations(all_df[all_df['fetal_health'] == 1.0])
    fig3 = plot_prolongued_decelerations(all_df[all_df['fetal_health'] == 2.0])
    fig4 = plot_prolongued_decelerations(all_df[all_df['fetal_health'] == 3.0])

    return plot_graphs_helper(window, fig1, fig2, fig3, fig4)


def plot_all_graphs(window, df):
    """
    Plots all graphs (FHS, Baseline FHR, Accelerations, Prolongued Decelerations) for given dataset
    :param window: Window object to plot graphs on
    :param df: Pandas DataFrame with fetal health data to be plotted
    :return: Canvas objects with figures plotted onto each canvas
    """
    fig1 = plot_fhs_overview(df)
    fig2 = plot_baseline_fhr(df)
    fig3 = plot_accelerations(df)
    fig4 = plot_prolongued_decelerations(df)

    return plot_graphs_helper(window, fig1, fig2, fig3, fig4)


def plot_correlation_matrix(df):
    """
    Creates a new window plotting a correlation matrix for fetal health data
    :param df: Pandas DataFrame of fetal health data
    :return: None
    """
    corr_matrix = df.corr()
    fig, ax = plt.subplots(figsize=(20, 15))
    ax = sns.heatmap(corr_matrix,
                     annot=True,
                     linewidths=0.5,
                     fmt=".2f",
                     cmap="YlGnBu")
    fig.tight_layout()
    fig.show()
