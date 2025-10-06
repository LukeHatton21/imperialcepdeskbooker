import streamlit as st
import pandas as pd
import datetime
import os
from PIL import Image
import csv
import altair as alt

# --- Config ---
rooms = {
    "601": [f"Desk {i}" for i in range(1, 9)],
    "602": [f"Desk {i}" for i in range(1, 9)],
    "604": [f"Desk {i}" for i in range(1, 13)],
    "605": [f"Desk {i}" for i in range(1, 10)]
}
booking_horizon = 7  # days in advance
BOOKINGS_FILE = "bookings.csv"
ROOM_FLOOR_FOLDER = "Rooms"

# --- Load or Initialize bookings ---
def format_date_for_csv(date_obj):
    # date_obj: datetime.date or pd.Timestamp
    return date_obj.strftime("%d %B")

def parse_date_from_csv(date_str):
    # date_str: e.g. '06 October'
    return datetime.datetime.strptime(date_str + f" {datetime.date.today().year}", "%d %B %Y").date()

if os.path.exists(BOOKINGS_FILE):
    bookings = pd.read_csv(BOOKINGS_FILE, quotechar='"')
    # Migration: support old 'Day-Date' column
    if "Day-Date" in bookings.columns and "Date-Month" not in bookings.columns:
        bookings["Date-Month"] = bookings["Day-Date"].apply(lambda x: " ".join(str(x).split()[1:3]) if len(str(x).split()) >= 3 else str(x))
        bookings = bookings.drop(columns=["Day-Date"])
    expected_cols = ["Date-Month", "Room", "Desk", "User"]
    if list(bookings.columns) != expected_cols:
        st.warning(f"CSV columns are {list(bookings.columns)}, expected {expected_cols}. Please fix the CSV file.")
    # No normalization needed for 'Date-Month'
else:
    bookings = pd.DataFrame(columns=["Date-Month", "Room", "Desk", "User"])

if "bookings" not in st.session_state:
    st.session_state.bookings = bookings

def normalize_bookings_date():
    if not st.session_state.bookings.empty:
        # Only keep 'Date-Month' as 'dd Month'
        if "Day-Date" in st.session_state.bookings.columns:
            st.session_state.bookings["Date-Month"] = st.session_state.bookings["Day-Date"].apply(lambda x: " ".join(str(x).split()[1:3]) if len(str(x).split()) >= 3 else str(x))
            st.session_state.bookings = st.session_state.bookings.drop(columns=["Day-Date"])

# --- User login screen ---
if "user" not in st.session_state:
    st.session_state.user = ""

if not st.session_state.user:
    st.title("👤 CEP Desk Booking App Login 2025/26")
    user_input = st.text_input("Enter your name to continue:")
    if st.button("Continue"):
        if user_input.strip() == "":
            st.warning("Please enter your name.")
        else:
            st.session_state.user = user_input.strip()
            st.rerun()
else:
    st.title(f"📅 CEP PhD Desk Bookings - Welcome {st.session_state.user}")

    # --- Logout button ---
    if st.button("Logout"):
        st.session_state.user = ""
        st.rerun()

    # --- Tabs ---
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["➕ Book a Desk", "❌ Cancel Booking", "🎫 Your Bookings", "📋 All Bookings", "🗺️ Floor Maps", "ℹ️ About"])

    with tab1:
        today = datetime.date.today()
        max_date = today + datetime.timedelta(days=booking_horizon)
        selected_date = st.date_input("Select a date:", min_value=today, max_value=max_date)

        # Format selected date for storage/display
        selected_date_str = format_date_for_csv(selected_date)

        # Check if user already has a booking that day (use boolean indexing)
        already_booked = not st.session_state.bookings[
            (st.session_state.bookings["Date-Month"] == selected_date_str) &
            (st.session_state.bookings["User"] == st.session_state.user)
        ].empty

        if already_booked:
            st.warning(f"You already have a booking on {selected_date_str}. You can only book one desk per day.")
        else:
            free_counts = []
            for room, desks in rooms.items():
                booked_desks = st.session_state.bookings[
                (st.session_state.bookings["Date-Month"] == selected_date_str)
                & (st.session_state.bookings["Room"] == room)
            ]["Desk"].tolist()
                free_count = len([d for d in desks if d not in booked_desks])
                free_counts.append({"Room": room, "Free Desks": free_count})

            free_df = pd.DataFrame(free_counts)

            # Display bar chart
            chart = (
            alt.Chart(free_df)
            .mark_bar()
            .encode(
                x=alt.X("Room:N", title="Room"),
                y=alt.Y("Free Desks:Q", title="Number of Free Desks"),
                color=alt.Color("Room:N", legend=None),
                tooltip=["Room", "Free Desks"]
            )
            .properties(width="container", height=300, title=f"Available Desks on {selected_date_str}")
        )
            st.altair_chart(chart, use_container_width=True)                                             
            
            
            room = st.selectbox("Select a room:", list(rooms.keys()))
            available_desks = rooms[room]

            # Filter out booked desks for that date and room
            same_day_room_bookings = st.session_state.bookings[
                (st.session_state.bookings["Date-Month"] == selected_date_str)
                & (st.session_state.bookings["Room"] == room)
            ]

            booked_desks = same_day_room_bookings["Desk"].tolist()
            free_desks = [desk for desk in available_desks if desk not in booked_desks]

            if not free_desks:
                st.error("No desks available for this room on the selected date.")
            else:
                desk = st.selectbox("Select a desk:", free_desks)
                if st.button("Book Desk"):
                    # Double-check desk still free before saving (prevents race conditions)
                    latest_bookings = st.session_state.bookings[
                        (st.session_state.bookings["Date-Month"] == selected_date_str)
                        & (st.session_state.bookings["Room"] == room)
                    ]
                    if desk in latest_bookings["Desk"].tolist():
                        st.error("Sorry, that desk was just booked by someone else.")
                    else:
                        new_booking = pd.DataFrame(
                            [[st.session_state.user, selected_date_str, room, desk]],
                            columns=["User", "Date-Month", "Room", "Desk"]
                        )
                        st.session_state.bookings = pd.concat(
                            [st.session_state.bookings, new_booking],
                            ignore_index=True
                        )
                        st.success(f"✅ {desk} booked successfully for {selected_date_str} in Room {room}.")


    with tab2:
        user_bookings = st.session_state.bookings[st.session_state.bookings["User"] == st.session_state.user]
        if not user_bookings.empty:
            cancel_booking = st.selectbox("Select a booking to cancel:", [f"{row['Date-Month']} - {row.Room} - {row.Desk}" for idx, row in user_bookings.iterrows()])
            if st.button("Cancel Booking"):
                cancel_date_str, cancel_room, cancel_desk = cancel_booking.split(" - ")
                mask = (
                    (st.session_state.bookings["Date-Month"] == cancel_date_str) &
                    (st.session_state.bookings["Room"] == cancel_room) &
                    (st.session_state.bookings["Desk"] == cancel_desk) &
                    (st.session_state.bookings["User"] == st.session_state.user)
                )
                st.session_state.bookings = st.session_state.bookings.drop(st.session_state.bookings[mask].index)
                normalize_bookings_date()
                st.session_state.bookings.to_csv(BOOKINGS_FILE, index=False)
                st.success(f"Cancelled booking for {cancel_desk} in {cancel_room} on {cancel_date_str} ✅")
        else:
            st.info("You have no bookings to cancel.")

    with tab3:
        display_cols = ["Date-Month", "Room", "Desk", "User"]
        your_bookings = st.session_state.bookings[st.session_state.bookings["User"] == st.session_state.user]
        if not your_bookings.empty:
            st.dataframe(your_bookings[display_cols].sort_values(by=["Date-Month"]))
        else:
            st.info("You have no bookings currently.")

    with tab4:
        vis_date_bookings = st.date_input("Select a date to view bookings:", min_value=today, max_value=max_date, key="tab3_date")
        display_cols = ["Date-Month", "Room", "Desk", "User"]
        vis_date_bookings_str = format_date_for_csv(vis_date_bookings)
        filtered_bookings = st.session_state.bookings[st.session_state.bookings["Date-Month"] == vis_date_bookings_str]
        if not filtered_bookings.empty:
            st.dataframe(filtered_bookings[display_cols].sort_values(by=["Room", "Desk"]))
        else:
            st.info("No bookings for this date.")

    with tab5:
        vis_date = st.date_input("Select a date to view floor maps:", min_value=today, max_value=max_date, key="map_date")
        vis_date_str = format_date_for_csv(vis_date)
        map_room = st.selectbox("Select a room to view floor map:", list(rooms.keys()))

        # Show desk booking status (use boolean indexing)
        room_bookings = st.session_state.bookings[
            (st.session_state.bookings["Date-Month"] == vis_date_str) &
            (st.session_state.bookings["Room"] == map_room)
        ]
        st.subheader("Desk Status")
        for d in rooms[map_room]:
            if d in room_bookings["Desk"].tolist():
                booked_by = room_bookings.loc[room_bookings["Desk"] == d, "User"].values[0]
                st.markdown(f"**{d}: Booked by {booked_by}**")
            else:
                st.markdown(f"**{d}: Free**")

        # Load floor layout image
        img_path = os.path.join(ROOM_FLOOR_FOLDER, f"{map_room}.png")
        if os.path.exists(img_path):
            img = Image.open(img_path)
            st.image(img, caption=f"Floor Layout Room {map_room}", width="stretch")
        else:
            st.warning(f"Floor layout image for room {map_room} not found.")

    with tab6:
        st.header("About This App")
        st.markdown("""
        This app allows CEP PhD students to book desks in the 6th floor rooms!
        
        **Features:**
        - Book a desk up to 7 days in advance.
        - View and cancel your bookings.
        - See overall bookings and desk availability.
        - View floor maps of rooms.

        **Usage Guidelines:**
        - Each user can only book one desk per day.
        - Please ensure to cancel bookings if you no longer need the desk.
                    

        For any issues or suggestions, please contact Luke Hatton or Eirini Sampson. We're currently trialling this as a booking system for the PhD desks so want to hear your feedback!
        """)

