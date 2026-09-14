function updateDateTime() {
  const offset = (window.CLOCK_OFFSET_MINUTES || 0) * 60 * 1000;
  let currentDate = new Date(Date.now() - offset)
  let days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
  let months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
  let day = days[currentDate.getDay()]
  let month = months[currentDate.getMonth()]
  let date = currentDate.getDate()
  // let year = currentDate.getFullYear()
  let hour = currentDate.getHours()
  let minute = currentDate.getMinutes()
  // let seconds = currentDate.getSeconds()
  let ampm = hour >= 12 ? 'PM' : 'AM'
  hour = hour % 12
  hour = hour ? hour : 12
  minute = minute < 10 ? '0' + minute : minute
  // let seconds = seconds < 10 ? '0' + seconds : seconds
  let formattedDate = day + ', ' + month + ' ' + date + ' // ' + hour + ':' + minute + ' ' + ampm
  document.getElementById('datetimeFooter').innerHTML = formattedDate
}
updateDateTime()
setInterval(updateDateTime, 1000)