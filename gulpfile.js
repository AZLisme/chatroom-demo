let gulp = require('gulp');
let pug = require('gulp-pug');
let uglify = require('gulp-uglify');
let stylus = require('gulp-stylus');
let rename = require('gulp-rename');

function addMinToPath(path) {
    path.basename += '.min';
}

gulp.task('default', function () {
    // 将你的默认的任务代码放在这
});

gulp.task('dist', function () {
    // Compile templates
    gulp.src('src/*.pug')
        .pipe(pug({
            compress: true
        }))
        .pipe(gulp.dest('./templates/'));

    // Compile CSS
    gulp.src('src/css/*.styl')
        .pipe(stylus({
            compress: true
        }))
        .pipe(rename(addMinToPath))
        .pipe(gulp.dest('./static/css/'));

    // Compile Javascripts
    gulp.src('src/js/*.js')
        .pipe(rename(addMinToPath))
        .pipe(gulp.dest('./static/js/'));

    let copyList = {
        "src/css/font.css": "static/css/",
        "src/css/material.min.css": "static/css/",
        "src/css/material.min.css.map": "static/css/",
        "src/css/material-font.woff2": "static/css/",
        "src/js/material.min.js": "static/js/",
        "src/js/material.min.js.map": "static/js/",
        "node_modules/jquery/dist/jquery.min.js": "static/js/",
        "node_modules/jquery/dist/jquery.min.js.map": "static/js/",
        "node_modules/socket.io-client/dist/socket.io.min.js": "static/js/",
        "node_modules/socket.io-client/dist/socket.io.min.js.map": "static/js/"
    };

    Object.keys(copyList).forEach(function (key) {
        let value = copyList[key];
        gulp.src(key).pipe(gulp.dest(value));
    });
});