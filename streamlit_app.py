import streamlit as st
import pandas as pd
import datetime
import os
from PIL import Image

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
if os.path.exists(BOOKINGS_FILE):
    bookings = pd.read_csv(BOOKINGS_FILE, parse_dates=["Date"])
else:
    bookings = pd.DataFrame(columns=["Date", "Room", "Desk", "User"])

if "bookings" not in st.session_state:
    st.session_state.bookings = bookings

# --- User login screen ---
if "user" not in st.session_state:
    st.session_state.user = ""

if not st.session_state.user:
    st.title("👤 Desk Booking App Login")
    user_input = st.text_input("Enter your name to continue:")
    if st.button("Continue"):
        if user_input.strip() == "":
            st.warning("Please enter your name.")
        else:
            st.session_state.user = user_input.strip()
            st.rerun()
else:
    st.title(f"📅 Desk Booking App - Welcome {st.session_state.user}")

    # --- Logout button ---
    if st.button("Logout"):
        st.session_state.user = ""
        st.rerun()

    # --- Tabs ---
    tab1, tab2, tab3, tab4 = st.tabs(["➕ Book a Desk", "❌ Cancel Booking", "📋 Current Bookings", "🗺️ Floor Maps"])

    with tab1:
        today = datetime.date.today()
        max_date = today + datetime.timedelta(days=booking_horizon)
        selected_date = st.date_input("Select a date:", min_value=today, max_value=max_date)

        # Check if user already has a booking that day
        already_booked = not st.session_state.bookings.query("Date == @selected_date and User == @st.session_state.user").empty

        if already_booked:
            st.warning(f"You already have a booking on {selected_date}. You can only book one desk per day.")
        else:
            room = st.selectbox("Select a room:", list(rooms.keys()))
            available_desks = rooms[room]
            booked_desks = st.session_state.bookings.query("Date == @selected_date and Room == @room")["Desk"].tolist()
            free_desks = [d for d in available_desks if d not in booked_desks]
            desk = st.selectbox("Select a desk:", free_desks if free_desks else ["No desks available"])

            if st.button("Book Desk"):
                if desk == "No desks available":
                    st.warning("No desks left in this room on this date.")
                else:
                    new_booking = {"Date": pd.to_datetime(selected_date), "Room": room, "Desk": desk, "User": st.session_state.user}
                    st.session_state.bookings = pd.concat([
                        st.session_state.bookings, pd.DataFrame([new_booking])
                    ], ignore_index=True)
                    st.session_state.bookings.to_csv(BOOKINGS_FILE, index=False)
                    st.success(f"Booked {desk} in {room} on {selected_date} for {st.session_state.user} ✅")

    with tab2:
        user_bookings = st.session_state.bookings.query("User == @st.session_state.user")
        if not user_bookings.empty:
            cancel_booking = st.selectbox("Select a booking to cancel:", [f"{row.Date.date()} - {row.Room} - {row.Desk}" for idx, row in user_bookings.iterrows()])
            if st.button("Cancel Booking"):
                cancel_date, cancel_room, cancel_desk = cancel_booking.split(" - ")
                cancel_date = pd.to_datetime(cancel_date)
                st.session_state.bookings = st.session_state.bookings.drop(
                    st.session_state.bookings[(st.session_state.bookings.Date == cancel_date) &
                                              (st.session_state.bookings.Room == cancel_room) &
                                              (st.session_state.bookings.Desk == cancel_desk) &
                                              (st.session_state.bookings.User == st.session_state.user)].index
                )
                st.session_state.bookings.to_csv(BOOKINGS_FILE, index=False)
                st.success(f"Cancelled booking for {cancel_desk} in {cancel_room} on {cancel_date.date()} ✅")
        else:
            st.info("You have no bookings to cancel.")

    with tab3:
        st.dataframe(st.session_state.bookings.sort_values(by=["Date", "Room", "Desk"]))

    with tab4:
        vis_date = st.date_input("Select a date to view floor maps:", min_value=today, max_value=max_date, key="map_date")
        map_room = st.selectbox("Select a room to view floor map:", list(rooms.keys()))

        # Load floor layout image
        img_path = os.path.join(ROOM_FLOOR_FOLDER, f"{map_room}.png")
        if os.path.exists(img_path):
            img = Image.open(img_path)
            st.image(img, caption=f"Floor Layout Room {map_room}", use_column_width=True)
        else:
            st.warning(f"Floor layout image for room {map_room} not found.")

        # Show desk booking status
        room_bookings = st.session_state.bookings.query("Date == @vis_date and Room == @map_room")
        st.subheader("Desk Status")
        for d in rooms[map_room]:
            if d in room_bookings["Desk"].tolist():
                booked_by = room_bookings.loc[room_bookings["Desk"] == d, "User"].values[0]
                st.markdown(f"**{d}: Booked by {booked_by}**")
            else:
                st.markdown(f"**{d}: Free**")
